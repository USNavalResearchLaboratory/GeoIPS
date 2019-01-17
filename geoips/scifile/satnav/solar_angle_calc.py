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

import numpy as np
from numpy import pi,cos,sin,arccos
from datetime import datetime, timedelta
from IPython import embed as shell

def solar_angle_calc(varname, dt, lons, lats):

    radlats = np.deg2rad(lats)
    radlons = np.deg2rad(lons)

    #Calculate fractional hours and fractional years
    #Note that the epoch time used here starts on Jan 1st at 12:00:00Z for whatever year we are in
    time_since_jan_1 = dt - datetime(dt.year, 1, 1, 0, 0, 0)

    #Fractional year (radians)
    fraction_year = 2*pi*time_since_jan_1.total_seconds()/timedelta(365).total_seconds()

    #Fractional hours since noon (hours)
    fraction_hour = time_since_jan_1.seconds/3600.0

    #Don't need HH because DOY includes fractional HHMMSS
    #Equation of time (minutes)
    eqtime = 229.18*(0.000075+(0.001868*cos(fraction_year))+(-0.032077*sin(fraction_year))+
                     (-0.014615*cos(2.0*fraction_year))+(-0.040849*sin(2.0*fraction_year)))

    #Solar declination (radians)
    dec = (0.006918-(0.399912*cos(fraction_year))+(0.070257*sin(fraction_year))-
           (0.006758*cos(2*fraction_year))+(0.000907*sin(2*fraction_year))-
           (0.002697*cos(3*fraction_year))+(0.00148*sin(3*fraction_year)))

    #Time offset (minutes)
    min_per_rad = 4*180/np.pi #4 min/degree converted to min/radians

    #time_offset = eqtime+(min_per_rad*radlons)
    ##True solar time (minutes)
    #true_solar_time = (fraction_hour*60.0)+time_offset
    ##Solar hour angle (radians)
    #hour_angle = (pi/180.0)*((true_solar_time/4.0)-180.0)

    ##Merged the above lines for speed
    #hour_angle2 = (pi/180.0)*(((eqtime+(4*180/np.pi*radlons)+(fraction_hour*60))/4.0)-180.0)

    #Simplied above line for speed (good luck redoing this)...
    #This removes all multiplication of the actual array speeds things up significantly
    #This makes for a difference on the order of a minute when calculating for goes high-res
    hour_angle = radlons + np.pi*(eqtime/720.0 + fraction_hour/12.0 - 1)


    #Calculate solar angles (radians)
    sin_lats = sin(radlats)
    cos_lats = cos(radlats)
    sun_zen = arccos((sin_lats*sin(dec))+(cos_lats*cos(dec)*cos(hour_angle)))
    if varname == 'SunAzimuth':
        sun_azm = arccos(((sin_lats*cos(sun_zen))-sin(dec))/(cos_lats*sin(sun_zen)))
        sun_azm *= 180.0/pi
        sun_azm -= 180
        sun_azm[sin(hour_angle) < 0] *= -1
    else:
        sun_zen *= 180.0/pi

    if varname == 'SunZenith':
        return sun_zen
    elif varname == 'SunAzimuth':
        return sun_azm
