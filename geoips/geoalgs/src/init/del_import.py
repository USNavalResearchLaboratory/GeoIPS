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
import argparse


# GeoIPS Libraries
# This must be imported this way since it is called from command line
# Probably means we should reorganize a bit, though
from add_import import get_import_name


def del_import(fname, imp_str, fortran=False):
    f = open(fname, 'r')
    lines = f.readlines()
    f.close()
    if "%s\n" % imp_str in lines:
        ind = lines.index(imp_str+'\n')
        lines.pop(ind)
        lines.pop(ind) #Removes extra line
        f = open(fname, 'w')
        f.writelines(lines)
        f.close()

    if fortran is True:
        imp_name = get_import_name(imp_str)
        imp_str = '%s.__doc__ = format_fortran_docstring(%s.__doc__)' % (imp_name, imp_name)
        f = open(fname, 'r')
        lines = f.readlines()
        f.close()
        if "%s\n" % imp_str in lines:
            ind = lines.index(imp_str+'\n')
            lines.pop(ind)
            lines.pop(ind) #Removes extra line
            f = open(fname, 'w')
            f.writelines(lines)
            f.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('fname')
    parser.add_argument('imp_str')
    parser.add_argument('--fortran', action='store_true', default=False)
    args = parser.parse_args()
    del_import(args.fname, args.imp_str, fortran=args.fortran)
