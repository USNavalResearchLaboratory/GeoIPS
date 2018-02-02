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


def get_import_name(imp_str):
    imp = imp_str.split('import')[1].strip()
    try:
        imp = imp.split('as')[1].strip()
    except IndexError:
        pass
    return imp

def has_import(fname, str):
    f = open(fname, 'r')
    lines = f.readlines()
    f.close()
    if "%s\n" % str in lines:
        return True
    else:
        return False

def del_import(fname, str, fortran=False):
    f = open(fname, 'r')
    lines = f.readlines()
    f.close()
    if "%s\n" % str in lines:
        ind = lines.index(str+'\n')
        lines.pop(ind)
        lines.pop(ind) #Removes extra line
        f.open(fname, 'w')
        f.writelines(lines)
        f.close()

def add_import(fname, imp_str, fortran=False):
    imp_str = imp_str.strip()
    if not has_import(fname, imp_str):
        init_file = open(fname, 'a+')
        init_file.write("%s\n\n" % imp_str)
        init_file.close()

    if fortran is True:
        imp_name = get_import_name(imp_str)
        imp_str = '%s.__doc__ = format_fortran_docstring(%s.__doc__)' % (imp_name, imp_name)
        if not has_import(fname, imp_str):
            init_file = open(fname, 'a+')
            init_file.write("%s\n\n" % imp_str)
            init_file.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('fname')
    parser.add_argument('imp_str')
    parser.add_argument('--fortran', action='store_true', default=False)
    parser.add_argument('--delete', action='store_true', default=False)
    args = parser.parse_args()
    if not args.delete:
        add_import(args.fname, args.imp_str, fortran=args.fortran)
    else:
        del_import(args.fname, args.imp_str, fortran=args.fortran)
