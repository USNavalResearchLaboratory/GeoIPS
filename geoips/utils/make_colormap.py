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


# Standard Python Libraries
import logging
import os
import sys
from glob import glob

#for remote debugging in wingware
try:
    import wingdbstub
except:
    print('Could not find wingdbstub from driver.py.  I hope you\'re not trying to dubug remotely...')


# Installed Libraries
from IPython import embed as shell


# GeoIPS Libraries
from geoips.sectorfile.xml_scrubber import XMLFile
from geoips.utils.log_setup import interactive_log_setup, root_log_setup
from geoips.utils.plugin_paths import paths as gpaths


root_logger, file_hndlr, email_hndlr = root_log_setup(loglevel='info', subject='none')
log = interactive_log_setup(logging.getLogger(__name__))


if len(sys.argv) < 2:
    log.info('Available colorbars:')
    for filename in glob(gpaths['GEOIPS']+'/geoips/geoimg/xml_palettes/*.xml'):
        elt_names = XMLFile(filename).element_names()
        log.info('File: '+filename)
        for cbname in elt_names:
            log.info('    Colorbar: '+cbname)
else:
    cbname = sys.argv[1]
    
    log.info('Creating colorbar '+cbname)

    for filename in glob(gpaths['GEOIPS'] +'/geoips/geoimg/xml_palettes/*.xml'):
        cb = XMLFile(filename).open_element(cbname)
        if cb:
            log.info('  From file '+filename+'\n')
            cb.write_colorbar()
