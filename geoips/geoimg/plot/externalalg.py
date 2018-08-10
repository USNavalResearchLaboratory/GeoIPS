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



plot_class_name = 'ExternalAlg'
plot_method_name = 'externalalg'
class ExternalAlg(GeoImgBase):

    @property
    def image(self):
        '''
        ExternalAlg is different than ExternalImg in that it takes in
        the entire datafile for processing (rather than pre-registered
        data), and returns an arbitrary array or dictionary of arrays 
        instead of an RGB image array).

        If a dictionary is returned, one image will be created per 
        dictionary entry (more specifically - self.plot will be called
        once per dictionary entry - you can either actually plot or 
        create data output from within self.plot)

        In order to handle the arbitrary output formats, an <alg>_plot
        and <alg>_coverage external algorithm must be created in addition
        to <alg>.  So there will be:

            geoalgs/src/<algname>/<algname>.py, 
            geoalgs/src/<algname>/<algname>_plot.py, 
            geoalgs/src/<algname>/<algname>_coverage.py, 

            ie
            geoalgs/src/winds/winds.py
            geoalgs/src/winds/winds_plot.py
            geoalgs/src/winds/winds_coverage.py
        '''
    
        
        # Only run the algoritm and set self.image once
        if not hasattr(self, '_image'):
            img_dts = {}
            pname = self.product.name
            sname = self.sector.name
            img_dts['start_fullext'+sname+pname] = datetime.utcnow()
            log.info('Entering external data-based algorithm.')

            '''
            Products are mapped one to one from productfiles/<platform_name>/<Product-Name>.xml
               to geoalgs/src/<product_name>.
             Convention for product names Is Capitalized first letter, with dashes between
               words (which get turned into spaces on display on the web).
             Convention for module names in geoalgs is all lower case with '_' between
               words.  Just convert product name to module name to get the appropriate 
               algorithm to run.
             See geoalgs/README.txt for more info on module/product naming.
            '''
            import geoips.geoalgs as geoalgs
            algorithm = getattr(geoalgs,self.product.name.lower().replace('-','_'))
            log.info('Using %s algorithm.' % algorithm)

            img_dts['start_runextalg'+sname+pname] = datetime.utcnow()
            '''
            Note with ExternalImg we pass the registered data to the algorithm - 
            Here we are passing the entire datafile, the algorithm can register
            as needed.
            Also note outdata can be any arbitrary array or dictionary of 
            arrays - it does not have to be an RGB image return.  You must
            Create an additional geoalg to handle the plotting and coverage
            checking (<alg>_plot and <alg>_coverage go with <alg>), since 
            the self.image array can be of arbitrary format.
            We may want to rename self.image and self.plot (since they can
            both handle data outputs as well as imagery output...) But I 
            am not ready to make that change just yet.
            '''
            outdata, metadata = algorithm(self.datafile,
                                self.sector,
                                self.product,
                                '',
                               )
            img_dts['end_runextdataalg'+sname+pname] = datetime.utcnow()

            '''
            NOTE all plotting routines flipud the data before setting the 
            image array. Not exactly sure why (maybe pyresample flipuds
            when registering?  If you don't register data for some reason
            and plots/data are upside down - check this.
            Put flipud in the individual algorithms if needed.
            '''
            self._image = outdata
            self.image_metadata = metadata

        return self._image

    def plot(self, imgkey=None):
        '''
        Note you must specify an external plot algorithm, that knows how to 
        handle whatever format of outdata arrays your external algorithm 
        produces. These should be specified as 
            geoalgs/src/<algname>, 
            geoalgs/src/<algname>_plot, 
            geoalgs/src/<algname>_coverage, 

        plot algorithm can either actually contain commands to plot data, 
            and/or output data arrays.

        self.plot gets called once per data array within the dictionary.
            perhaps this should be changed to just pass the entire 
            self.image to self.plot, and not have a special case in 
            process.py ....?
        '''

        img_dts = {}
        prodname = self.product.name.lower().replace('-','_')
        pname = self.product.name
        sname = self.sector.name

        import geoips.geoalgs as geoalgs
        algorithm = getattr(geoalgs, '%s_plot'%prodname)
        log.info('Using %s plotting algorithm.'%algorithm)
        img_dts['start_runextalgplot'+sname+pname] = datetime.utcnow()
        algorithm(self, imgkey=imgkey)
        img_dts['end_runextdataalgplot'+sname+pname] = datetime.utcnow()

    def coverage(self, imgkey=None):
        '''Tests self.image to determine what percentage of the image is filled with good data.
        This test assumes that pixels where self.image.mask is True are bad values and does not
        count those pixels towards the coverage percentage.

        Note you must specify an external coverage algorithm, that knows how to 
        handle whatever format of outdata arrays your external algorithm 
        produces. These should be specified as 
            geoalgs/src/<algname>, 
            geoalgs/src/<algname>_plot, 
            geoalgs/src/<algname>_coverage, 

        self.plot gets called once per data array within the dictionary.
            perhaps this should be changed to just pass the entire 
            self.image to self.plot, and not have a special case in 
            process.py ....?

        '''

        img_dts = {}
        prodname = self.product.name.lower().replace('-','_')
        pname = self.product.name
        sname = self.sector.name

        import geoips.geoalgs as geoalgs
        algorithm = getattr(geoalgs, '%s_coverage'%prodname)
        log.info('Using %s coverage check algorithm.'%algorithm)
        img_dts['start_runextalgcovg'+sname+pname] = datetime.utcnow()
        covg = algorithm(self.image, imgkey=imgkey)
        img_dts['end_runextdataalgcovg'+sname+pname] = datetime.utcnow()

        return covg 
