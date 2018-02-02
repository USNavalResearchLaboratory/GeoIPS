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

from solar_angle_calc import solar_angle_calc
from IPython import embed as shell

function_map = {'SunZenith': solar_angle_calc,
                'SunAzimuth': solar_angle_calc,
               }

def satnav(varname, dt, lons, lats, index=None):
    try:
        func = function_map[varname]
    except KeyError:
        raise KeyError('Unable to find function to calculate %s.' % varname)

    if index is not None:
        lats = lats[index]
        lons = lons[index]
    else:
        pass

    return func(varname, dt, lons, lats)
