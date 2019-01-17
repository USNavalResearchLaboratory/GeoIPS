#!/usr/bin/env python

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

# Standard Python Libraries
import re
from math import pi, cos


# Installed Libraries
from IPython import embed as shell


# GeoIPS Libraries


def center_to_corner(lat_0, lon_0, dx, dy, nl, ns):
    '''
    Calculate the minimum and maximum latitudes and longitudes
    based on center latitude, center longitude, pixel width,
    pixel height, number of lines, and number of samples.

    Returns a tuple of tuples of the form: ((minLat, maxLat), (minLon, maxLon))

    :docnote:`Should probably check to be sure that lines and samples are in the correct order here.`

    +------------+---------+-------------------------------------------+
    | Parameter: | Type:   | Description:                              |
    +============+=========+===========================================+
    | lat_0      | *float* | Center latitude in degrees                |
    +------------+---------+-------------------------------------------+
    | lon_0      | *float* | Center longitude in degrees               |
    +------------+---------+-------------------------------------------+
    | dx         | *float* | Pixel size in km along reference parallel |
    +------------+---------+-------------------------------------------+
    | dy         | *float  | Pixel size in km along reference meridian |
    +------------+---------+-------------------------------------------+
    | nl         | *int*   | Number of pixels along reference meridian |
    +------------+---------+-------------------------------------------+
    | ns         | *int*   | Number of pixels along reference parallel |
    +------------+---------+-------------------------------------------+

    '''
    #Set up constants
    a0 = 6.3781*10**6 #radius of earth in meters 
    c0 = 2*pi*a0 #Circumference of earth
    KMperLat = c0/360000.0 #Number of km per degree latitude

    #Convert latitude and longitude to numeric form
    #   Longitude range = [-180:180]
    lat_0 = convert_lat_to_num(lat_0)
    lon_0 = convert_lon_to_num(lon_0)

    #Calculate latitudes
    llcrnrlat = lat_0
    urcrnrlat = lat_0
    dLat = (dx*nl)/(KMperLat)
    llcrnrlat -= dLat/2
    urcrnrlat += dLat/2
    if llcrnrlat < -90: llcrnrlat = -90
    if urcrnrlat > 90: urcrnrlat = 90
    #Reverse for longitude calculation if below equator
    if lat_0 < 0:
        llcrnrlat, urcrnrlat = reverse_args(llcrnrlat, urcrnrlat)

    #Calculate longitudes
    llcrnrlon = lon_0
    urcrnrlon = lon_0
    if (llcrnrlat > 0):
        circumf = 2*pi*a0*cos( (llcrnrlat)*(pi/180) )
    elif (urcrnrlat < 0):
        circumf = 2*pi*a0*cos( (urcrnrlat)*(pi/180) )
    else:
        circumf = 2*pi*a0*cos( (urcrnrlat + llcrnrlat)*(pi/180) )
    KMperLon = circumf/360000
    dLon = (dy*ns)/(KMperLon)
    try:
        assert dLon <= 360, ('Either dy or ns is too large.  dLon must be less than or equal to 180.'
            +'\n\tdLon = %s, dy = %s, ns = %s' % (str(dLon), str(dy), str(ns)))
    except AssertionError:
        shell()
    llcrnrlon -= dLon/2
    urcrnrlon += dLon/2
    llcrnrlon = convert_360_to_180(llcrnrlon)
    urcrnrlon = convert_360_to_180(urcrnrlon)
    
    #If reversed for longitude calculation, put back in order
    if lat_0 < 0:
        llcrnrlat, urcrnrlat = reverse_args(llcrnrlat, urcrnrlat)

    return llcrnrlat, llcrnrlon, urcrnrlat, urcrnrlon


def corner_to_center(min_lat, max_lat, min_lon, max_lon, nl, ns):
    '''
    Calcualate the center latitude, center longitude, pixel width,
    and pixel height of a sector based on its minimum and maximum
    latitude and longitude, the number of lines, and the number of
    samples.

    Returns a tuple of the form (lat_0, lon_0, pixWidth, pixHeight)

    :docnote:`Should probably check to be sure that lines and samples are in the correct order here.`

    +------------+---------+-----------------------------------------------+
    | Parameter: | Type:   | Description:                                  |
    +============+=========+===============================================+
    | min_lat    | *float* | Minimum latitude in degrees                   |
    +------------+---------+-----------------------------------------------+
    | max_lat    | *float* | Maximum latitude in degrees                   |
    +------------+---------+-----------------------------------------------+
    | min_lon    | *float* | Minimum longitude in degrees                  |
    +------------+---------+-----------------------------------------------+
    | max_lon    | *float* | Maximum longitude in degrees                  |
    +------------+---------+-----------------------------------------------+
    | nl         | *int*   | Number of pixels along the reference meridian |
    +------------+---------+-----------------------------------------------+
    | ns         | *int*   | Number of pixels along the reference parallel |
    +------------+---------+-----------------------------------------------+

    '''
    #Set up constants
    a0 = 6.3781*10**6 #radius of earth in meters 
    c0 = 2*pi*a0 #Circumference of earth
    KMperLat = c0/360000.0 #Number of km per degree latitude

    #Convert latitude and longitude to numeric form
    #   Longitude range = [-180:180]
    min_lat = convert_lat_to_num(min_lat)
    max_lat = convert_lat_to_num(max_lat)
    min_lon = convert_360_to_180(convert_lon_to_num(min_lon))
    max_lon = convert_360_to_180(convert_lon_to_num(max_lon))

    #Calc center lat/lon
    dLat = max_lat - min_lat
    dLon = max_lon - min_lon
    lat_0 = dLat/2 + min_lat
    lon_0 = dLon/2 + min_lon
    lon_0 = convert_360_to_180(lon_0)

    #Calc dx, dy
    dx = (dLat*KMperLat)/nl

    if (min_lat > 0):
        circumf = 2*pi*a0*cos( (min_lat)*(pi/180) )
    elif (max_lat < 0):
        circumf = 2*pi*a0*cos( (max_lat)*(pi/180) )
    else:
        circumf = 2*pi*a0*cos( (max_lat + min_lat)*(pi/180) )
    KMperLon = circumf/360000
    dy = (dLon*KMperLon)/ns

    return lat_0, lon_0, dx, dy


def convert_lat_to_num(lat):
    '''
    Converts latitude to [-90:90] given latitude between '90S' and '90N'.

    +------------+-------+--------------------------------------------+
    | Parameter: | Type: | Description:                               |
    +============+=======+============================================+
    | lat        | *str* | Latitude in degrees north or south ending  |
    |            |       | with an `N` for north and an `S` for south |
    +------------+-------+--------------------------------------------+

    '''

    #Test whether a direct conversion to float can be made
    #   Return the result if it does not fail
    try:
        lat = float(lat)
        assert -90 <= lat <= 90, 'Latitude=%s out of range.' % str(lat)
        return lat
    except ValueError:
        pass

    #Split given string into parts.
    #Part 1: The number
    #Part 2: The quadrant designator (NS)
    #Part 3: Null string
    #If any of these parts are not correct, will fail at some point.
    nsew = re.compile('([NSns])')
    lat_parts = nsew.split(lat, maxsplit=1)
    #Raise AssertionError if N or S were not found or more than
    #   one match occurred
    if len(lat_parts) != 3 or lat_parts[2] != '':
        raise AssertionError('Latitude is not formatted correctly (%s).  '
            'Must be float, a string easily converted to a float, or of the form 90.0N.' % lat)
    
    try:
        temp_lat = float(lat_parts[0])
        #Raise an assertion error if the number is negative.  Should
        #   never have negative values with a quadrant designator.
        if temp_lat < 0: raise ValueError
    #Raise an attribute error if conversion to float fails.  This means
    #   that there were still non-float like characters in the string.
    except ValueError:
        raise AssertionError('Latitude is not formatted correctly (%s).  '
            'Must be float, a string easily converted to a float, or of the form 90.0N.' % lat)

    #Modify number as needed based on the quadrant designator.
    #   Raise an attribute error if value is out of range.
    quadrant = lat_parts[1].upper()
    if quadrant == 'N':
        lat = temp_lat
        assert lat <= 90, 'Latitude must be between -90 and 90 or 90S and 90N.'
    elif quadrant == 'S':
        lat = -temp_lat
        assert lat >= -90, 'Latitude must be between -90 and 90 or 90S and 90N.'

    return lat


def convert_lon_to_num(lon):
    '''
    Converts longitude to [-180:180] given longitude between '180W' and '180E'
    or [0:360]

    +------------+-------+------------------------------------------+
    | Parameter: | Type: | Description:                             |
    +============+=======+==========================================+
    | lon        | *str* | Lonitude in degrees east or west ending  |
    |            |       | with an `E` for east and an `W` for west |
    +------------+-------+------------------------------------------+
    '''

    #Test whether a direct conversion to float can be made
    #   Return the result if it does not fail
    try:
        lon = float(lon)
        lon = convert_360_to_180(lon)
        return lon
    except ValueError:
        pass

    #Split given string into parts.
    #Part 1: The number
    #Part 2: The quadrant designator (EW)
    #Part 3: Null string
    #If any of these parts are not correct, will fail at some point.
    nsew = re.compile('([EWew])')
    lon_parts = nsew.split(lon, maxsplit=1)
    #Raise AssertionError if N or S were not found or more than
    #   one match occurred
    if len(lon_parts) != 3 or lon_parts[2] != '':
        raise AssertionError('Longitude is not formatted correctly (%s).  '
            'Must be float, a string easily converted to a float, or of the form 180.0W.' % lon)

    try:
        temp_lon = float(lon_parts[0])
        #Raise an assertion error if the number is negative.  Should
        #   never have negative values with a quadrant designator.
        if temp_lon < 0: raise ValueError
    #Raise an attribute error if conversion to float fails.  This means
    #   that there were still non-float like characters in the string.
    except ValueError:
        raise AssertionError('Longitude is not formatted correctly (%s).  '
            'Must be float, a string easily converted to a float, or of the form 180.0W.' % lon)

    #Modify number as needed based on the quadrant designator.
    #   Raise an attribute error if value is out of range.
    quadrant = lon_parts[1].upper()
    if quadrant == 'E':
        lon = temp_lon
        assert lon <= 180, 'Longitude must be between -180 and 180, 0 and 360, or 180S and 180N.'
    elif quadrant == 'W':
        lon = -temp_lon
        assert lon >= -180, 'Longitude must be between -180 and 180, 0 and 360, or 180S and 180N.'

    return lon


def convert_360_to_180(lon):
    '''
    Converts longitude in [0:360] to [-180:180]

    +------------+---------+----------------------+
    | Parameter: | Type:   | Description:         |
    +============+=========+======================+
    | lon        | *float* | Longitude in degrees |
    +------------+---------+----------------------+

    '''
    if lon > 180:
        lon -= 360
    return lon


def convert_180_to_360(lon):
    '''
    Converts longitude in [-180:180] to [0:360]

    +------------+---------+----------------------+
    | Parameter: | Type:   | Description:         |
    +============+=========+======================+
    | lon        | *float* | Longitude in degrees |
    +------------+---------+----------------------+

    '''
    if lon < 0:   lon += 360
    if lon > 360: lon -= 360
    return lon


def reverse_args(*args):
    '''
    Apparently this referses whatever arguments are input.

    :docnote:`I have no idea what this would have been used for, but it seems stupid.`

    '''
    args = list(args)
    args.reverse()
    return args
