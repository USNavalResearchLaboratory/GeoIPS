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

# Installed Libraries
import numpy as np
from scipy.signal import convolve2d

# GeoIPS Libraries
from ..lib.libstddev_kernel import stddev_kernel


viirs_var_map = {'BT4': 'SVM13BT',
                 'BT11': 'SVM15BT'}
modis_var_map = {'BT4': 'modis_ch20',
                 'BT11': 'modis_ch31'}

sensor_var_maps = {'viirs': viirs_var_map,
                   'modis': modis_var_map}


def night_fires(datafile, sector, product, workpath):

    # Make sure the input datafile has been registered and get the area definition
    if not datafile.registered and len(datafile.variables) > 1:
        raise ValueError('Multiple data resolutions encountered.  Data must be registered.')

    # Get the appropriate variable name map for the input datafile based on sensor name
    try:
        var_map = sensor_var_maps[datafile.source_name]
    except KeyError:
        raise ValueError('Unrecognized sensor {}.  Accepted sensors include: {}'.format(
                         (datafile.source_name, ', '.join(sensor_var_maps.keys()))))

    # Gather the correct data into the correct variables for each variable
    bt4 = datafile.variables[var_map['BT4']]
    bt11 = datafile.variables[var_map['BT11']]

    chan_diff = bt4 - bt11
    stddev_chan_diff = np.ma.masked_array(stddev_kernel(chan_diff.data, 3, 3, mask=chan_diff.mask), mask=chan_diff.mask)

    # Find all "fire" pixels
    fires = np.zeros(chan_diff.shape)
    fires[np.ma.where((chan_diff > 4.0) & (stddev_chan_diff > 6.0))] = 1.0

    # Find all "hot spot" pixels
    hot = np.zeros(chan_diff.shape)
    hot[np.ma.where((chan_diff > 20.0) & (fires > 0.0))] = 1.0

    # Expand fire and hot spot pixels a bit to make them show up in imagery
    kernel = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])

    fires = convolve2d(fires, kernel, mode='same', boundary='fill', fillvalue=0)
    fires[np.where(fires > 0)] = 1

    hot = convolve2d(hot, kernel, mode='same', boundary='fill', fillvalue=0)
    hot[np.where(hot > 0)] = 1

    red = fires
    grn = hot
    blu = np.zeros(chan_diff.shape, dtype=np.int)

    img = np.dstack((red, grn, blu))
    img = np.ma.array(img, dtype=np.float, mask=np.dstack((chan_diff.mask, chan_diff.mask, chan_diff.mask)))

    return img
