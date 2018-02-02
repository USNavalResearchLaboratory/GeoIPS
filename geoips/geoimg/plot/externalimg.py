# Author:
#    Naval Research Laboratory, Marine Meteorology Division
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the NRLMMD License included with this program.  If you did not
# receive the license, see http://www.nrlmry.navy.mil/geoips for more
# information.
#
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# included license for more details.

# Python Standard Libraries
import logging
import os
from datetime import datetime


# Installed Libraries
import numpy as np

try:
    from IPython import embed as shell
except:
    print 'Failed import IPython in geoimg/plot/rgbimg.py. If you need it, install it.'


# GeoIPS Libraries
from .geoimgbase import GeoImgBase
from geoips.utils.memusg import print_mem_usage
from geoips.utils.log_setup import interactive_log_setup



log = interactive_log_setup(logging.getLogger(__name__))



plot_class_name = 'ExternalImg'
plot_method_name = 'external'
class ExternalImg(GeoImgBase):

    @property
    def image(self):
        if not hasattr(self, '_image'):
            img_dts = {}
            pname = self.product.name
            sname = self.sector.name
            img_dts['start_fullext'+sname+pname] = datetime.utcnow()
            log.info('Entering external algorithm.')

            #Products are mapped one to one from productfiles/<platform_name>/<Product-Name>.xml
            #   to geoalgs/src/<product_name>.
            # Convention for product names Is Capitalized first letter, with dashes between
            #   words (which get turned into spaces on display on the web).
            # Convention for module names in geoalgs is all lower case with '_' between
            #   words.  Just convert product name to module name to get the appropriate 
            #   algorithm to run.
            # See geoalgs/README.txt for more info on module/product naming.
            import geoips.geoalgs as geoalgs
            algorithm = getattr(geoalgs,self.product.name.lower().replace('-','_'))
            log.info('Using %s algorithm.' % algorithm)

            img_dts['start_runextalg'+sname+pname] = datetime.utcnow()
            outdata = algorithm(self.registered_data,
                                self.sector,
                                self.product,
                                '',
                               )
            img_dts['end_runextalg'+sname+pname] = datetime.utcnow()

            # 20160203  Is this creating 2 copies of outdata ?!
            red = outdata[...,0]
            grn = outdata[...,1]
            blu = outdata[...,2]

            #Make alpha layer
            alp = np.zeros(red.shape, dtype=np.bool)
            for img in [red, grn, blu]:
                try:
                    if img.mask is not np.False_:
                        alp += img.mask
                except AttributeError:
                    pass
            #You will get yelled at by numpy if you removed the "alp.dtype" portion of this.
            #   It thinks you are trying to cast alp to be an integer.
            alp = np.array(alp, dtype=np.float)
            alp -= np.float(1)
            alp *= np.float(-1)

            img_dts['start_flipudext'+sname+pname] = datetime.utcnow()
            #print_mem_usage(self.logtag+'gimgbeforeflipud',True)
            self._image = np.flipud(np.dstack([red.data, grn.data, blu.data, alp]))
            img_dts['end_flipudext'+sname+pname] = datetime.utcnow()
            img_dts['end_fullext'+sname+pname] = datetime.utcnow()
            #print_mem_usage(self.logtag+'gimgafterflipud',True)
            for sttag in sorted(img_dts.keys()):
                if 'start_' in sttag:
                    tag = sttag.replace('start_','')
                    try:
                        log.info('process image time %-40s: '%tag+str(img_dts['end_'+tag]-img_dts['start_'+tag])+' '+socket.gethostname())
                    except:
                        log.info('WARNING! No end time for '+sttag)
        return self._image

    # 20160203 monitor - small mem jump (~200M) at self.basemap.imshow
    #@profile
    def plot(self):
        #Figure and axes
        self._figure, self._axes = self._create_fig_and_ax()

        #self.basemap.imshow(self.image, ax=self.axes, interpolation='none')
        self.basemap.imshow(self.image, ax=self.axes, interpolation='nearest')
        if self.is_final:
            self.finalize()

    def coverage(self):
        '''Tests self.image to determine what percentage of the image is filled with good data.
        This test assumes that pixels where self.image.mask is True are bad values and does not
        count those pixels towards the coverage percentage.

        Returns the percent coverage as a float.'''
        return 100*float(np.where(self.image[...,3] > 0)[0].size)/self.image[...,3].size

