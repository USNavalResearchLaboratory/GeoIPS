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
from matplotlib import cm, colors

try:
    from IPython import embed as shell
except:
    print 'Failed import IPython in geoimg/plot/rgbimg.py. If you need it, install it.'


# GeoIPS Libraries
from .geoimgbase import GeoImgBase
from ..mpl_utils import create_color_gun
from geoips.utils.gencolormap import get_cmap
from geoips.utils.memusg import print_mem_usage
from geoips.utils.log_setup import interactive_log_setup



log = interactive_log_setup(logging.getLogger(__name__))



plot_class_name = 'BasicImg'
plot_method_name = 'basic'
class BasicImg(GeoImgBase):

    @property
    def interp_method(self):
        # Leave with default that is in scifile/containers.py
        # Need to specify in productfile if you want different interpolation
        self._interp_method = None
        if self.product.interpmethod:
            self._interp_method = str(self.product.interpmethod)
        return self._interp_method

    @property
    def image(self):
        if not hasattr(self, '_image'):
            img_dts = {}
            pname = self.product.name
            sname = self.sector.name
            img_dts['start_fullsingleimg'+sname+pname] = datetime.utcnow()
            log.info('Creating basic image.')
            print_mem_usage(self.logtag+'gimgbeforeregister',True)

            #Register data to area definition
            #Performing prior to color gun generation in order to allow
            #   for multiple data resolutions

            gun = self.product.images['img']

            img_dts['start_clrgunsingle'+sname+pname] = datetime.utcnow()
            self._image = np.flipud(create_color_gun(self.registered_data, gun))
            img_dts['end_clrgunsingle'+sname+pname] = datetime.utcnow()
            colormapper = cm.ScalarMappable(norm=colors.NoNorm(), cmap=get_cmap(self.product.cmap))
            img_dts['start_torgbasingle'+sname+pname] = datetime.utcnow()
            self._image = colormapper.to_rgba(self.image)
            img_dts['end_torgbasingle'+sname+pname] = datetime.utcnow()
            log.info(sname+pname+' Done Creating single channel image.')
            img_dts['end_fullsingleimg'+sname+pname] = datetime.utcnow()

            for sttag in sorted(img_dts.keys()):
                if 'start_' in sttag:
                    tag = sttag.replace('start_','')
                    try:
                        log.info('process image time %-40s: '%tag+str(img_dts['end_'+tag]-img_dts['start_'+tag])+' '+socket.gethostname())
                    except:
                        log.info('WARNING! No end time for '+sttag)
        return self._image


    def plot(self):
        #Figure and axes
        self._figure, self._axes = self._create_fig_and_ax()
        #self.axes.legend(loc=4,fontsize='small')

        #self.basemap.imshow(self.image, ax=self.axes, interpolation='none')
        self.basemap.imshow(self.image, ax=self.axes, interpolation='nearest')
        if self.is_final:
            self.finalize()

    def coverage(self):
        '''Tests self.image to determine what percentage of the image is filled with good data.
        This test assumes that pixels where self.image.mask is True are bad values and does not
        count those pixels towards the coverage percentage.

        Returns the percent coverage as a float.'''
        #try:
        #    return 100*float(self.image.count())/self.image.size
        #except AttributeError:
        #    return 100*float(np.count_nonzero(self.image[:,:,3]))/self.image[:,:,3].size
        #return 100*float(self.image.count())/self.image.size
        return 100*float(np.where(self.image[...,3] > 0)[0].size)/self.image[...,3].size

