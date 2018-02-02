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


def convert_bool_to_yes_no(vals):
    '''Converts a list of boolean (True/False) values to
    a list of "yes"/"no" strings for use in terascan calls.'''
    while True:
        try:
            ind = vals.index(True)
            if vals[ind] is not True:
                vals[ind] = '%r' % vals[ind]
            else:
                vals[ind] = 'yes'
        except ValueError:
            break
    while True:
        try:
            ind = vals.index(False)
            if vals[ind] is not False:
                vals[ind] = '%r' % vals[ind]
            else:
                vals[ind] = 'no'
        except ValueError:
            break

def convert_tdf_to_str(vals):
    for ind, val in enumerate(vals):
        try:
            vals[ind] = val.name
        except AttributeError:
            pass

def convert_none_to_null(vals):
    while True:
        try:
            ind = vals.index(None)
            vals[ind] = ''
        except ValueError:
            break

def convert_args_to_str(args):
    '''Recieves a dict of arguments (probably for a terascan call),
    converts any boolean (True/False) values to "yes"/"no" strings
    and any other non-string values to strings.  All values must be
    scalars.'''
    keys = args.keys()
    vals = args.values()
    convert_tdf_to_str(vals)
    convert_bool_to_yes_no(vals)
    convert_none_to_null(vals)
    vals = [str(x) for x in vals]
    args = dict(zip(keys, vals))
    return args

def convert_type_tdf_to_python(type):
    '''Recieves the name of a TDF data types as a string (e.g. output
    from the varinfo command with attr_value=type) and returns the
    equivalent python type for use in numpy array initialization.'''
    conv_dict = {'byte':'ubyte', 'short':'short', 'long':'i', 'float':'f', 'double':'double'}
    return conv_dict[type]
