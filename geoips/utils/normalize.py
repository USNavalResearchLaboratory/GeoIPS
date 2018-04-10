#!/bin/env python

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


# Installed Libraries
import numpy as np
from IPython import embed as shell


# GeoIPS Libraries


# Changed bounds defaults to crop to match geoimg/geoimg.py.apply_data_range and productfile/xml.py.outbounds
# Does not appear normalize is ever used with defaults for bounds.
def normalize(data, min_val=None, max_val=None, min_bounds='crop', max_bounds='crop'):

    #Determine if mask is currently hardened
    hardmask = None
    if hasattr(data, 'hardmask'):
        hardmask = data.hardmask

    #Harden the mask to avoid unmasking bad values
    if hardmask is False:
        data.harden_mask()

    if min_val == None:
        min_val = data.min()
    if max_val == None:
        max_val = data.max()
    if min_bounds is None:
        min_bounds = 'retain'
    if max_bounds is None:
        max_bounds = 'retain'

    data = data.copy()
    data -= min_val
    data *= abs(1.0/(max_val - min_val))

    if min_bounds == 'retain':
        pass
    elif min_bounds == 'crop':
        data[np.ma.where(data < 0.0)] = 0.0
    elif min_bounds == 'mask':
        data = np.ma.masked_less(data, 0.0)

    if max_bounds == 'retain':
        pass
    elif max_bounds == 'crop':
        data[np.ma.where(data > 1.0)] = 1.0
    elif max_bounds == 'mask':
        data = np.ma.masked_greater(data, 1.0)


    #If the mask was originally not hardened, then unharden it now
    if hardmask is False:
        data.soften_mask()

    return data

