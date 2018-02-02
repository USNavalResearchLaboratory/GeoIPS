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
import os
import socket

from IPython import embed as shell

paths = {}

dynamic_subdir = '/dynamic'
static_subdir = '/static'
tctemplate = '/template_tc_sectors.xml'
volcanotemplate = '/template_volcano_sectors.xml'

subdirs = {}
# These are all relative to GeoIPS by default.
subdirs['SECTORFILEPATHS']='/geoips/sectorfiles'
subdirs['PRODUCTFILEPATHS']='/geoips/productfiles'
subdirs['STATIC_SECTORFILEPATHS'] = '/geoips/sectorfiles'+static_subdir
subdirs['TEMPLATEPATHS'] = '/geoips/sectorfiles'+dynamic_subdir
subdirs['TC_TEMPLATEFILES'] = '/geoips/sectorfiles'+dynamic_subdir+tctemplate
subdirs['VOLCANO_TEMPLATEFILES'] = '/geoips/sectorfiles'+dynamic_subdir+volcanotemplate
subdirs['PALETTEPATHS']='/geoips/geoimg/ascii_palettes'
subdirs['TESTPALETTEPATHS']='/geoips/geoimg/test_palettes'
subdirs['XMLPALETTEPATHS']='/geoips/geoimg/xml_palettes'
subdirs['DOWNLOADSITEPATHS']='/geoips/downloaders/Sites'
subdirs['READERPATHS']='/geoips/scifile/readers'
subdirs['GEOALGSPATHS']='/geoips/geoalgs/src'


# At a minimum, GEOIPS_OUTDIRS must be defined.
paths['GEOIPS_OUTDIRS'] = os.getenv('GEOIPS_OUTDIRS')

# If GEOIPS is not defined, we must have a system install.
# Set GEOIPS to current path (get rid of utils/plugin_paths.py)
paths['GEOIPS'] = os.getenv('GEOIPS')
if not os.getenv('GEOIPS'):
    paths['GEOIPS'] = os.path.split(os.path.dirname(__file__))[0]+'/..'

paths['GEOIPS_SCRIPTS'] = ''
if os.getenv('GEOIPS_SCRIPTS'):
    paths['GEOIPS_SCRIPTS'] = os.getenv('GEOIPS_SCRIPTS')
elif os.getenv('UTILSDIR'):
    paths['GEOIPS_SCRIPTS'] = os.getenv('UTILSDIR')


paths['BOXNAME'] = socket.gethostname()



paths['SCRATCH'] = os.getenv('SCRATCH')
if not os.getenv('SCRATCH'):
    paths['SCRATCH'] = os.getenv('GEOIPS_OUTDIRS')+'/scratch'
paths['LOCALSCRATCH'] = os.getenv('LOCALSCRATCH')
if not os.getenv('LOCALSCRATCH'):
    paths['LOCALSCRATCH'] = paths['SCRATCH']
paths['SHAREDSCRATCH'] = os.getenv('SHAREDSCRATCH')
if not os.getenv('SHAREDSCRATCH'):
    paths['SHAREDSCRATCH'] = paths['SCRATCH']



# SATOPS is the default intermediate and ancillary data location.
paths['SATOPS'] = os.getenv('SATOPS')
if not os.getenv('SATOPS'):
    paths['SATOPS'] = os.getenv('GEOIPS_OUTDIRS')+'/satops'

paths['STANDALONE_GEOIPS'] = os.getenv('STANDALONE_GEOIPS')
if not os.getenv('STANDALONE_GEOIPS'):
    paths['STANDALONE_GEOIPS'] = paths['GEOIPS']

paths['EXTERNAL_GEOIPS'] = os.getenv('EXTERNAL_GEOIPS')
if not os.getenv('EXTERNAL_GEOIPS'):
    paths['EXTERNAL_GEOIPS'] = ''

paths['LOGDIR'] = os.getenv('LOGDIR')
if not os.getenv('LOGDIR'):
    paths['LOGDIR'] = paths['GEOIPS_OUTDIRS']+'/logs'


paths['GEOIPSTEMP'] = os.getenv('GEOIPSTEMP')
if not os.getenv('GEOIPSTEMP'):
    paths['GEOIPSTEMP'] = paths['SATOPS']+'/intermediate_files/GeoIPStemp'
paths['GEOIPSFINAL'] = os.getenv('GEOIPSFINAL')
if not os.getenv('GEOIPSFINAL'):
    paths['GEOIPSFINAL'] = paths['SATOPS']+'/intermediate_files/GeoIPSfinal'


# NOTE THIS IS NOT A LIST
paths['AUTOGEN_DYNAMIC_SECTORFILEPATH'] = paths['SATOPS']+'/longterm_files/sectorfiles/dynamic'

# NOTE THIS IS NOT A LIST
if os.getenv('EXTERNAL_AUTOGEN_DYNAMIC_SECTORFILEPATH'):
    paths['AUTOGEN_DYNAMIC_SECTORFILEPATH'] = os.getenv('EXTERNAL_AUTOGEN_DYNAMIC_SECTORFILEPATH')

# Now, if the user has set environment variables specifying plugin directories, add them here.

# This specifies entire packages in alternate locations
extgeoips = paths['EXTERNAL_GEOIPS']
standalone_geoips = paths['STANDALONE_GEOIPS']

# External paths, set in bashrc. None if non-existent.
for envvar in ['SECTORFILEPATH','PRODUCTFILEPATH','STATIC_SECTORFILEPATH',
                'TEMPLATEPATH','TC_TEMPLATEFILE','VOLCANO_TEMPLATEFILE',
                'PALETTEPATH','TESTPALETTEPATH','XMLPALETTEPATH',
                'DOWNLOADSITEPATH','READERPATH','GEOALGSPATH']:
    # Defined as EXTERNAL_SECTORFILEPATH in bashrc
    ext_envvar = os.getenv('EXTERNAL_'+envvar)
    # Used internall as SECTORFILEPATHS
    paths_varname = envvar+'S'

    # Default for paths_varname
    paths[paths_varname] = [paths['GEOIPS']+subdirs[paths_varname]]

    # Default to STANDALONE_GEOIPS if defined in bashrc
    if standalone_geoips:
        paths[paths_varname] = [paths['STANDALONE_GEOIPS']+subdirs[paths_varname]]

    # Set to explicit EXTERNAL paths defined in bashrc to paths_varname
    # This REPLACES the default list, so everything you want must be listed 
    # in bashrc.
    if ext_envvar:
        # DO NOT include defaults
        paths[paths_varname] = []
        if envvar == 'SECTORFILEPATH':
            paths['STATIC_SECTORFILEPATHS'] = []
            paths['TEMPLATEPATHS'] = []
            paths['TC_TEMPLATEFILE'] = []
            paths['VOLCANO_TEMPLATEFILE'] = []
        for path in ext_envvar.split(':'):
            #print 'EXTERNAL_'+paths_varname+' path '+path
            if os.path.isdir(path):
                paths[paths_varname] += [path]
            # Set these relative to SECTORFILEPATHS (will get overwritten 
            # with env vars later if they are explicitly set).
            if envvar == 'SECTORFILEPATH':
                paths['STATIC_SECTORFILEPATHS'] += [path+static_subdir]
                paths['TEMPLATEPATHS'] += [path+dynamic_subdir]
                paths['TC_TEMPLATEFILE'] += [path+dynamic_subdir+tctemplate]
                paths['VOLCANO_TEMPLATEFILE'] += [path+dynamic_subdir+volcanotemplate]
    # If EXTERNAL_GEOIPS is defined, use the appropriate relative path there
    # But ONLY if ext_envvar is not set (ext_envvar OVERRIDES).
    elif extgeoips:
        for path in extgeoips.split(':'):
            extgeoipspath = path+subdirs[paths_varname]
            #print 'EXTERNAL_GEOIPS path '+extgeoipspath
            if os.path.isdir(extgeoipspath) and extgeoipspath not in paths[paths_varname]:
                paths[paths_varname] += [extgeoipspath]
    else:
        #print 'DEFAULT '+envvar+' GEOIPS path '+str(paths[paths_varname])
        pass

