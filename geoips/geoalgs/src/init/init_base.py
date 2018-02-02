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
from collections import OrderedDict

def format_fortran_docstring(docstr):
    lines = docstr.split('\n')

    #Deconstruct docstring
    docstring_parts = OrderedDict()
    for line in lines:
        if len(line) > 0:
            if not line[0].isspace():
                currkey = line
                docstring_parts[currkey] = []
            else:
                docstring_parts[currkey].append(line)

    #Put together output docstring
    outdoclines = []
    for key, vals in docstring_parts.items():
        outdoclines.append(key)
        for val in vals:
            outdoclines.append(val)
        outdoclines.append('\n')
    return '\n'.join(outdoclines)
