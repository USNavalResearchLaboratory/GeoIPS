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
import sys


# Installed Libraries
try:
    from IPython import embed as shell
except:
    print 'Failed IPython import in create_init.py. If you need it, install it.'


init_header = '''
#!/bin/env python

# This file generated automatically by make.  Edit at your own risk.
# If this file appears to be corrupted or incorrect, try running "make config".
# If that still does not fix the problem, run "make clean" followed by "make".
# If problems persist, remove the geoalgs/lib directory, then run "make".
# Any further problems should be directed to the Naval Research Laboratory
# Marine Meteorolgy Division.
# Web: http://www.nrlmry.navy.mil/geoips
# Email: geoips@nrlmry.navy.mil

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

from collections import OrderedDict

def format_fortran_docstring(docstr):
    lines = docstr.split('\\n')

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
        outdoclines.append('\\n')
    return '\\n\\n'.join(outdoclines)

'''

def create_init(init_fname):
    init_file = open(init_fname, 'w')
    init_file.writelines(init_header)
    init_file.close()

if __name__ == '__main__':
    init_fname = sys.argv[1]
    create_init(init_fname)
