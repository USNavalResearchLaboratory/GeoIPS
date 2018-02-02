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
from ..mpl_utils import create_color_gun
from .geoimgbase import GeoImgBase
from geoips.utils.log_setup import interactive_log_setup



log = interactive_log_setup(logging.getLogger(__name__))



plot_class_name = 'RGBImg'
plot_method_name = 'rgb'
class RGBImg(GeoImgBase):

    @property
    def image(self):
        '''
        Convert array, list, or dictionary of three MxN arrays to MxNx4 RGBA array.
        '''
        if not hasattr(self, '_image'):
            img_dts = {}
            pname = self.product.name
            sname = self.sector.name
            img_dts['start_fullrgb'+sname+pname] = datetime.utcnow()
            log.info('Creating RGB image.')

            #Register data to area definition
            #Performing prior to color gun generation in order to allow
            #   for multiple data resolutions

            #Create Red, Grn, Blu guns
            img_dts['start_clrgnrgb'+sname+pname] = datetime.utcnow()
            rgb_data = {}
            for gun in self.product.images.values():
                log.info('\tStarting %s' % gun.name)
                rgb_data[gun.name] = create_color_gun(self.registered_data, gun)
                log.info('\tDone with %s' % gun.name)

            try:
                red = rgb_data['red']
                grn = rgb_data['grn']
                blu = rgb_data['blu']
            except KeyError:
                red = rgb_data['RED']
                grn = rgb_data['GRN']
                blu = rgb_data['BLU']
            img_dts['end_clrgnrgb'+sname+pname] = datetime.utcnow()

            #Make alpha layer
            mask = np.zeros(red.shape, dtype=np.bool)
            for img in [red, grn, blu]:
                try:
                    mask += np.ma.getmaskarray(img)
                except AttributeError:
                    pass
            alp = np.zeros(red.shape, dtype=np.int)
            alp[~mask] = 1

            img_dts['start_flipudrgb'+sname+pname] = datetime.utcnow()
            self._image = np.flipud(np.dstack([red.data, grn.data, blu.data, alp]))
            img_dts['end_flipudrgb'+sname+pname] = datetime.utcnow()
            img_dts['end_fullrgb'+sname+pname] = datetime.utcnow()

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
