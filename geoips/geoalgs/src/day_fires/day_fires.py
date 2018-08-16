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


viirs_var_map = {'REF': 'SVM07Ref',
                 'BT4': 'SVM13BT',
                 'BT11': 'SVM15BT'}
modis_var_map = {'REF': 'modis_ch02',
                 'BT4': 'modis_ch20',
                 'BT11': 'modis_ch31'}

sensor_var_maps = {'viirs': viirs_var_map,
                   'modis': modis_var_map}


def day_fires(datafile, sector, product, workpath):
    # Make sure the input datafile has been registered and get the area definition
    if not datafile.registered or len(datafile.variables) > 1:
        raise ValueError('Multiple data resolutions encountered.  Data must be registered.')

    # Get the appropriate variable name map for the input datafile based on sensor name
    try:
        var_map = sensor_var_maps[datafile.source_name]
    except KeyError:
        raise ValueError('Unrecognized sensor {}.  Accepted sensors include: {}'.format(
            (datafile.source_name, ', '.join(sensor_var_maps.keys()))))

    # Gather the correct data into the correct variables for each variable
    ref = datafile.variables[var_map['REF']]
    bt4 = datafile.variables[var_map['BT4']]
    bt11 = datafile.variables[var_map['BT11']]

    # Multiply reflectances by 100 to make % reflectance
    ref *= 100

    chan_diff = bt4 - bt11
    stddev_chan_diff = np.ma.masked_array(stddev_kernel(chan_diff.filled(0), 3, 3), mask=chan_diff.mask)
    # Filled bt11 with bt11.min() prior to stddev calculation to avoid skewing
    #   calculation with very abnormal fill values.
    stddev_bt11 = np.ma.masked_array(stddev_kernel(bt11.filled(bt11.min()), 3, 3), mask=bt11.mask)

    # Find all "fire" pixels
    fire_pix = np.ma.where((ref < 30.0) &
                           # (chan_diff > 20.0) &
                           (chan_diff > 10.0) &
                           (stddev_chan_diff > 6.0) &
                           (bt4 > 40.0) & (stddev_bt11 < 2.5))
    fires = np.zeros(chan_diff.shape)
    fires[fire_pix] = 1.0

    # Find all "hot spot" pixels
    hot_pix = np.ma.where((chan_diff > 30.0) & (fires > 0.0))
    hot = np.zeros(chan_diff.shape)
    hot[hot_pix] = 1.0

    # Expand fire and hot spot pixels a bit to make them show up in imagery
    kernel = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])

    fires = convolve2d(fires, kernel, mode='same', boundary='fill', fillvalue=0)
    fires[np.where(fires > 0)] = 1

    hot = convolve2d(hot, kernel, mode='same', boundary='fill', fillvalue=0)
    hot[np.where(hot > 0)] = 1

    red = fires
    grn = hot
    blu = np.zeros(chan_diff.shape)

    img = np.dstack((red, grn, blu))
    img = np.ma.array(img, dtype=np.float)

    return img
