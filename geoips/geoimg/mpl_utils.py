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
from collections import OrderedDict
import textwrap


# Installed Libraries
import numpy as np
import matplotlib
from math import ceil
from IPython import embed as shell

# GeoIPS Libraries
from geoips.utils.normalize import normalize
from geoips.utils.log_setup import interactive_log_setup



log = interactive_log_setup(logging.getLogger(__name__))



def on_draw(event):
    '''Auto-wraps all text objects in a figure at draw-time'''
    log.debug('Running on-draw.')
    fig = event.canvas.figure

    #Cycle through all artists in all the axes in the figure
    for ax in fig.axes:
        for artist in ax.get_children():
            #If it's a text artist, wrap it...
            if isinstance(artist, matplotlib.text.Text):
                autowrap_text(artist, event.renderer)

    #Temporarily disconnect any callbacks to the draw event
    #(to avoid recursion)
    func_handles = fig.canvas.callbacks.callbacks[event.name]
    fig.canvas.callbacks.callbacks[event.name] = {}
    #Re-draw the figure
    fig.canvas.draw()
    #Reset the draw event callbacks
    fig.canvas.callbacks.callbacks[event.name] = func_handles
    log.debug('Done with on-draw.')

def autowrap_text(textobj, renderer):
    '''
    Wraps the given matplotlib text object so that it does not exceed the boundaries
    of the axis it is plotted in.
    '''
    log.debug('Running autowrap_text.')
    #Get the starting position of the text in pixels
    x0, y0 = textobj.get_transform().transform(textobj.get_position())
    #Get the extents of the current axis in pixels
    clip = textobj.get_axes().get_window_extent()
    #Set the text to rotate about the left edge (doesn't make sense otherwise)
    textobj.set_rotation_mode('anchor')

    # Get the amount of space in the direction of rotation to the left and 
    # right of x0, y0 (left and right are relative to the rotation, as well)
    rotation = textobj.get_rotation()
    right_space = min_dist_inside((x0, y0), rotation, clip)
    left_space = min_dist_inside((x0, y0), rotation - 180, clip)

    # Use either the left or right distance depending on the horiz alignment.
    alignment = textobj.get_horizontalalignment()
    if alignment is 'left':
        new_width = right_space
    elif alignment is 'right':
        new_width = left_space
    else:
        new_width = 2 * min(left_space, right_space)

    # Estimate the width of the new size in characters...
    aspect_ratio = 0.5 # This varies with the font!! 
    fontsize = textobj.get_size()
    pixels_per_char = aspect_ratio * renderer.points_to_pixels(fontsize)

    # If wrap_width is < 1, just make it 1 character
    wrap_width = max(1, new_width // pixels_per_char)
    wrapper = textwrap.TextWrapper(width=wrap_width, break_long_words=False, break_on_hyphens=False)
    try:
        wrapped_text = wrapper.fill(textobj.get_text())
    except TypeError:
        # This appears to be a single word
        wrapped_text = textobj.get_text()
    textobj.set_text(wrapped_text)
    log.debug('Done with autowrap_text.')

def min_dist_inside(point, rotation, box):
    """Gets the space in a given direction from "point" to the boundaries of
    "box" (where box is an object with x0, y0, x1, & y1 attributes, point is a
    tuple of x,y, and rotation is the angle in degrees)"""
    from math import sin, cos, radians
    x0, y0 = point
    rotation = radians(rotation)
    distances = []
    threshold = 0.0001 
    if cos(rotation) > threshold: 
        # Intersects the right axis
        distances.append((box.x1 - x0) / cos(rotation))
    if cos(rotation) < -threshold:
        # Intersects the left axis 
        distances.append((box.x0 - x0) / cos(rotation))
    if sin(rotation) > threshold:
        # Intersects the top axis
        distances.append((box.y1 - y0) / sin(rotation))
    if sin(rotation) < -threshold: 
        # Intersects the bottom axis
        distances.append((box.y0 - y0) / sin(rotation))
    return min(distances)

def parallels(sector):
    '''
    Calculates the parallels (latitude lines) that fall within the input sector.

    +-----------+--------+-----------------------------+
    | Parameter | Type   | Description                 |
    +===========+========+=============================+
    | sector    | Sector | A SectorFile.Sector object. |
    +-----------+--------+-----------------------------+
    '''

    # MLS this needs to be called before llcrnrlat, etc are set
    #     on master_info. 
    # MLS 20151205 Doesn't work for polar sectors, lat corners could all
    # be the same
    #corners = sector.area_definition.corners
    #lats = [np.rad2deg(corn.lat) for corn in corners]
    # MLS 20151205 Need to look at all of the actual lat vals to find
    # min/max. Was getting error ValueError: max() arg is an empty sequence
    # in self.basemap.drawparallels
    lats = sector.area_definition.get_lonlats()[1]
    log.info('Masking parallels lats')
    mlats = np.ma.masked_greater(lats,90)
    grid_size = sector.plot_info.grid_size
    min_parallel = ceil(float(mlats.min())/grid_size)*grid_size
    max_parallel = ceil(float(mlats.max())/grid_size)*grid_size
    parallels = drange(min_parallel, max_parallel, grid_size)
    log.info('Done masking parallels lats')
    return parallels

def drange(start, stop, step):
    '''
    Create a list of doubles containing the linear progression between start and stop.
    The spacing between the numbers is defined by step.
    This is intended to operate the same as `range()`, but can operate on floats.

    +-----------+-----------+------------------------------------------+
    | Parameter | Type      | Description                              |
    +===========+===========+==========================================+
    | start     | numerical | The starting value for the output range. |
    +-----------+-----------+------------------------------------------+
    | stop      | numerical | The ending value for the output range.   |
    +-----------+-----------+------------------------------------------+
    | step      | numerical | Space between values.                    |
    +-----------+-----------+------------------------------------------+
    '''

    r = start
    data = []
    while r < stop:
        data.append(r)
        r += step
    return data

def meridians(sector):
    '''
    Calculates the meridians (longitude lines) that fall within the input sector.

    +-----------+--------+-----------------------------+
    | Parameter | Type   | Description                 |
    +===========+========+=============================+
    | sector    | Sector | A SectorFile.Sector object. |
    +-----------+--------+-----------------------------+
    '''

    corners = sector.area_definition.corners
    lons = [np.rad2deg(corn.lon) for corn in corners]
    llcrnrlon = lons[3]
    urcrnrlon = lons[1]

    # Needed for full disk - need to generalize so it works for both.
    ##mlons = np.ma.masked_greater(sector.area_definition.get_lonlats()[0],180)
    ##corners = mlons.min(),mlons.max()
    ###lons = [np.rad2deg(corn.lon) for corn in corners]
    ##llcrnrlon = corners[0]
    ##urcrnrlon = corners[1]


    cent_lon = sector.area_info.center_lon_float
    if urcrnrlon < cent_lon < llcrnrlon:
        urcrnrlon += 360
    elif urcrnrlon < llcrnrlon:
        llcrnrlon -= 360
    # Default to "grid_size" if grid_lon_size is not specified.
    try:
        grid_size = sector.plot_info.grid_lon_size
    except AttributeError:
        grid_size = sector.plot_info.grid_size
    min_meridian = ceil(float(llcrnrlon)/grid_size)*grid_size
    max_meridian = ceil(float(urcrnrlon)/grid_size)*grid_size
    meridians_to_draw = np.arange(min_meridian, max_meridian, grid_size)
    meridian_wrap = np.where(meridians_to_draw >= 360)
    meridians_to_draw[meridian_wrap] -= 360
    return meridians_to_draw

def apply_data_range(data, min_val=None, max_val=None, min_outbounds='crop', max_outbounds='crop', norm=True, inverse=False):
    '''
    Apply minimum and maximum values to an array of data.

    +------------+----------------------------------------------------------------+
    | Parameters | Description                                                    |
    +============+================================================================+
    | data       | Array of data where isinstance(numpy.ndarray) is True.         |
    +------------+----------------------------------------------------------------+

    +-----------+-------------------------------------------------------------------------------+
    | Keywords  | Description                                                                   |
    +===========+===============================================================================+
    | min_val   | The minimum bound to be applied to the input data as a scalar.                |
    |           | Default: None                                                                 |
    +-----------+-------------------------------------------------------------------------------+
    | max_val   | The maximum bound to be applied to the input data as a scalar.                |
    |           | Default: None                                                                 |
    +-----------+-------------------------------------------------------------------------------+
    | min_outbounds | Method to use when applying bounds as a string.                               |
    |               | Valid values are:                                                             |
    |               | retain: keep all pixels as is                                                 |
    |               | mask: mask all pixels that are out of range.                                  |
    |               | crop: set all out of range values to either min_val or max_val as appropriate |
    |               | Default: 'crop' (to match default found in productfile/xml.py and utils/normalize.py)|
    +-----------+-------------------------------------------------------------------------------+
    | max_outbounds | Method to use when applying bounds as a string.                               |
    |               | Valid values are:                                                             |
    |               | retain: keep all pixels as is                                                 |
    |               | mask: mask all pixels that are out of range.                                  |
    |               | crop: set all out of range values to either min_val or max_val as appropriate |
    |               | Default: 'crop' (to match default found in productfile/xml.py and utils/normalize.py)|
    +-----------+-------------------------------------------------------------------------------+
    | norm      | Boolean flag indicating whether to normalize (True) or not (False).           |
    |           | If True, returned data will be in the range from 0 to 1.                      |
    |           | If False, returned data will be in the range from min_val to max_val.         |
    |           | Default: True (to match default found in productfile/xml.py)                  |
    +-----------+-------------------------------------------------------------------------------+
    | inverse   | Boolean flag indicating whether to inverse (True) or not (False).             |
    |           | If True, returned data will be inverted                                       |
    |           | If False, returned data will not be inverted                                  |
    |           | Default: True (to match default found in productfile/xml.py)                  |
    +-----------+-------------------------------------------------------------------------------+
    '''
    #Invert data if minimum value is greater than maximum value
    if inverse or (min_val is not None and max_val is not None and min_val > max_val):
        data, min_val, max_val = invert_data_range(data, min_val, max_val)

    #If a minimum value is specified, then apply minimum value
    if min_val is not None:
        data = apply_minimum_value(data, min_val, min_outbounds)
    else:
        min_val = data.min()

    #If a maximum value is specified, then apply maximum value
    if max_val is not None:
        data = apply_maximum_value(data, max_val, max_outbounds)
    else:
        max_val = data.max()


    # CHANGE DEFAULTS FOR OUTBOUNDS TO NONE??  If you want it to crop, specify.
    # Need to change in productfile/xml.py and utils/normalize.py
    # Actually, when plotting if you don't crop, it probably crops anyway. 
    #   so maybe keep 'crop' as default anyway ?

    #Normalize data if requested
    if norm is True:
        data = normalize(data, min_val, max_val, min_outbounds, max_outbounds)
    return data

def invert_data_range(data, min_val, max_val):
    log.info('Inverting data between %r and %r' % (min_val, max_val))
    if min_val > max_val:
        min_val, max_val = max_val, min_val
    data = max_val - (data - min_val)
    return data, min_val, max_val

def apply_minimum_value(data, min_val, outbounds):
    log.info('Applying minimum value of %r' % min_val)

    #Determine if mask is currently hardened
    hardmask = data.hardmask
    #Harden the mask to avoid unmasking bad values
    if hardmask is False:
        data.harden_mask()

    #If outbounds is set to "mask" then mask the out of range data
    if outbounds == 'mask':
        data = np.ma.masked_less(data, min_val)
    #If outbounds set to crop, then set out of range data to the minimum value
    elif outbounds == 'crop':
        data[data < min_val] = min_val
    else:
        raise ValueError('outbounds must be either "mask" or "crop".  Got %s.' % outbounds)

    #If the mask was originally not hardened, then unharden it now
    if hardmask is False:
        data.soften_mask()

    return data

def apply_maximum_value(data, max_val, outbounds):
    log.info('Applying maximum value of %r' % max_val)

    #Determine if mask is currently hardened
    hardmask = data.hardmask
    #Harden the mask to avoid unmasking bad values
    if hardmask is False:
        data.harden_mask()

    #If outboudns is set to "mask" then mask the out of range data
    if outbounds == 'mask':
        data = np.ma.masked_greater(data, max_val)
    #If outbounds is set to crop, then set out of range data to the maximum value
    elif outbounds == 'crop':
        data[data > max_val] = max_val
    else:
        raise ValueError('outbounds must be either "mask" or "crop".  Got %s.' % outbounds)

    #If the mask was originally not hardened, then unharden it now
    if hardmask is False:
        data.soften_mask()

    return data

def remove_unneeded_returns(equations, returns):
    '''
    Tests the equatiosn to determine whether all of the entries contained
    in returns are still required.  Each return's entry can be quite large.
    We can save memroy here by throwing out extra stuff.
    '''
    joined_args = ' '.join(equations.values())
    for key in returns.keys():
        if key not in joined_args:
            del returns[key]
    return returns

def apply_equations(data, equations):
    '''
    Applys a set of equations from a productfile.Image object to data.

    NOTE: This function should likely be replaced by a class in productfile.python
          when it is time to re-work productfile.py
    '''
    eq_returns = OrderedDict()
    eq_names = equations.keys()
    for eq_name in eq_names:
        #Remote extra return values
        eq_returns = remove_unneeded_returns(equations, eq_returns)
        #Get the current equation
        # DO NOT POP!  passed by reference, so it REMOVES the equations 
        #       from self.product.images['img'].equations!!!
        #       doesn't work when trying to use equations again for 
        #       processing merged imagery.
        eq = equations[eq_name]
        #Replace all channel references in the equation with data[chan.name]
        for chan_name in data.keys():
            eq = eq.replace(chan_name, 'data["%s"]' % chan_name)
        #Replace all previously calculated euqations in current equation
        for eq_ret_name in eq_returns.keys():
            eq = eq.replace(eq_ret_name, 'eq_returns["%s"]' % eq_ret_name)
        #Evaluate current equation
        log.info('Evaluating: %s = %s' % (eq_name, eq))
        eq_returns[eq_name] = eval(eq)
    ret_data = eq_returns[eq_name]
    return ret_data

def create_color_gun(datafile, gun):
    log.info('Processing %s gun.' % gun.name)
    variables = gun.required_variables
    geolocation_variables = gun.required_geolocation_variables
    #Make sure solar zenith angles exist if zenith correction is to be applied
    #Test channel units to make sure they are of the same type
    #*********************************
    #
    # Skipping units stuff for now!  Need to implement!
    #
    #*********************************

    temp_data = {}
    #Loop over data sources and variables
    for source_name, source_vars in variables.items():
        for var_name in source_vars:
            temp_data[var_name] = datafile.variables[var_name]
            if source_name.variables[var_name].zenith_correct and 'SunZenith' in datafile.geolocation_variables.keys():
                log.info('Applying Solar Zenith Correction to variable '+var_name)
                temp_data[var_name] = temp_data[var_name] / np.cos(np.deg2rad(datafile.geolocation_variables['SunZenith']))
    for source_name, source_gvars in geolocation_variables.items():
        for gvar_name in source_gvars:
            temp_data[gvar_name] = datafile.geolocation_variables[gvar_name]

        #Convert min and max values to current channel units
        #*****************************
        #
        # Skipping units stuff for now!  Need to implement!
        #
        #*****************************
        #min_val = chan.min
        #max_val = chan.max

        #Apply data range arguments
        #Includes channel inversion, min/max bounds, and normalization
        #temp_data[chan.name] = apply_data_range(chan_data, min_val, max_val, chan.outbounds, chan.normalize)
        #Apply unit conversions as needed
        #*****************************
        #
        # Skipping units stuff for now!  Need to implement!
        #
        #*****************************
        #temp_data[chan.name] = chan_data

    #Apply equations to the data
    gun_data = apply_equations(temp_data, gun.equations)
    #If the minimum value is larger than the maxim7um value for the gun, invert the gun
    #shell()
    # Defaults are set in productfile/xml.py.  outbounds -> crop, normalize->True, inverse->False
    gun_data = apply_data_range(gun_data, gun.min, gun.max, gun.min_outbounds, gun.max_outbounds, gun.normalize, gun.inverse)
    #Apply gamma corrections
    if gun.gamma is not None:
        for ind, gamma in enumerate(gun.gamma):
            log.info('Using %r as gamma correction for #%r for %s gun.' % (gamma, ind+1, gun.name))
            gun_data = gun_data**(1.0/float(gamma))

    return gun_data

