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



plot_class_name = 'BlankImg'
plot_method_name = 'blank'
class BlankImg(GeoImgBase):
    ''' This image class is useful for creating blank imagery to view area_definitions
    and plotting characteristics.  Please do not delete. Note it is totally untested 
    at this time - may need some work to make it actually plot.'''

    @property
    def image(self):
        pass
        self._image = something
        return self._image

    def plot(self):
        #Figure and axes
        self._figure, self._axes = self._create_fig_and_ax()
        self.basemap.imshow(self.image, ax=self.axes, interpolation='none')
        if self.is_final:
            self.finalize()

    def coverage(self):
        ''' Just return 100.0% coverage so BlankImg always gets produced.'''
        return 100.0
