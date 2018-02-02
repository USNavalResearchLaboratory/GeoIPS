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
import os, sys, shutil


def module_doc(docpath, modulepath):
    #Copy the module's rst file to documentation source directory
    modulename = os.path.basename(modulepath.strip('/'))
    src = "%s/%s.rst" % (modulename, modulename)
    doc = docpath+'/source/%s.rst' % (modulename)
    shutil.copyfile(src, doc)

    #Add module name to geoalgs_modules.txt
    pmod_file = open(docpath+'/source/geoalgs_modules.txt', 'a')
    pmod_file.write('    %s\n' % (modulename))
    pmod_file.close()

if __name__ == "__main__":
    docpath = sys.argv[1]
    modulepath = sys.argv[2]
    module_doc(docpath, modulepath)
