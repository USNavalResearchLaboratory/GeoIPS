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

dynamic_subdir = os.path.join('dynamic')
static_subdir = os.path.join('static')
tctemplate = os.path.join('template_tc_sectors.xml')
volcanotemplate = os.path.join('template_volcano_sectors.xml')

subdirs = {}
# These are all relative to GeoIPS by default.
subdirs['SECTORFILEPATHS']=os.path.join('geoips','sectorfiles')
subdirs['PRODUCTFILEPATHS']=os.path.join('geoips','productfiles')
subdirs['STATIC_SECTORFILEPATHS'] = os.path.join('geoips','sectorfiles',static_subdir)
subdirs['TEMPLATEPATHS'] = os.path.join('geoips','sectorfiles',dynamic_subdir)
subdirs['TC_TEMPLATEFILES'] = os.path.join('geoips','sectorfiles',dynamic_subdir,tctemplate)
subdirs['VOLCANO_TEMPLATEFILES'] = os.path.join('geoips','sectorfiles',dynamic_subdir,volcanotemplate)
subdirs['PALETTEPATHS']=os.path.join('geoips','geoimg','ascii_palettes')
subdirs['TESTPALETTEPATHS']=os.path.join('geoips','geoimg','test_palettes')
subdirs['XMLPALETTEPATHS']=os.path.join('geoips','geoimg','xml_palettes')
subdirs['DOWNLOADSITEPATHS']=os.path.join('geoips','downloaders','Sites')
subdirs['READERPATHS']=os.path.join('geoips','scifile','readers')
subdirs['GEOALGSPATHS']=os.path.join('geoips','geoalgs','src')


# At a minimum, GEOIPS_OUTDIRS must be defined.
paths['GEOIPS_OUTDIRS'] = os.getenv('GEOIPS_OUTDIRS')

# Location for writing out presectored data files, but unregistered
if os.getenv('PRESECTORED_DATA_PATH'):
    paths['PRESECTORED_DATA_PATH'] = os.getenv('PRESECTORED_DATA_PATH')
else:
    paths['PRESECTORED_DATA_PATH'] = os.path.join(paths['GEOIPS_OUTDIRS'],'preprocessed','sectored')

# Location for writing out preread, but unsectored/registered, data files
if os.getenv('PREREAD_DATA_PATH'):
    paths['PREREAD_DATA_PATH'] = os.getenv('PREREAD_DATA_PATH')
else:
    paths['PREREAD_DATA_PATH'] = os.path.join(paths['GEOIPS_OUTDIRS'],'preprocessed','unsectored')

# Location for writing out preregistered data files, but no algorithms applied
if os.getenv('PREREGISTERED_DATA_PATH'):
    paths['PREREGISTERED_DATA_PATH'] = os.getenv('PREREGISTERED_DATA_PATH')
else:
    paths['PREREGISTERED_DATA_PATH'] = os.path.join(paths['GEOIPS_OUTDIRS'],'preprocessed','registered')

# Location for writing out precalculated data files (algorithms applied)
if os.getenv('PRECALCULATED_DATA_PATH'):
    paths['PRECALCULATED_DATA_PATH'] = os.getenv('PRECALCULATED_DATA_PATH')
else:
    paths['PRECALCULATED_DATA_PATH'] = os.path.join(paths['GEOIPS_OUTDIRS'],'preprocessed','algorithms')

# GEOIPS_COPYRIGHT determines what organization name displays in imagery titles, etc.
paths['GEOIPS_COPYRIGHT'] = 'NRL-Monterey'
if os.getenv('GEOIPS_COPYRIGHT'):
    paths['GEOIPS_COPYRIGHT'] = os.getenv('GEOIPS_COPYRIGHT')

# If GEOIPS is not defined, we must have a system install.
# Set GEOIPS to current path (get rid of utils/plugin_paths.py)
paths['GEOIPS'] = os.getenv('GEOIPS')
if not os.getenv('GEOIPS'):
    paths['GEOIPS'] = os.path.join(os.path.split(os.path.dirname(__file__))[0],'..')

paths['GEOIPS_SCRIPTS'] = ''
if os.getenv('GEOIPS_SCRIPTS'):
    paths['GEOIPS_SCRIPTS'] = os.getenv('GEOIPS_SCRIPTS')
elif os.getenv('UTILSDIR'):
    paths['GEOIPS_SCRIPTS'] = os.getenv('UTILSDIR')


paths['GEOIPS_RCFILE'] = ''
if os.getenv('GEOIPS_RCFILE'):
    paths['GEOIPS_RCFILE'] = os.getenv('GEOIPS_RCFILE')


paths['BOXNAME'] = socket.gethostname()
paths['HOME'] = os.getenv('HOME')
if not os.getenv('HOME'):
    # Windows
    paths['HOME'] = os.getenv('HOMEDRIVE')+os.getenv('HOMEPATH')

paths['SCRATCH'] = os.getenv('SCRATCH')
if not os.getenv('SCRATCH'):
    paths['SCRATCH'] = os.path.join(os.getenv('GEOIPS_OUTDIRS'),'scratch')
paths['LOCALSCRATCH'] = os.getenv('LOCALSCRATCH')
if not os.getenv('LOCALSCRATCH'):
    paths['LOCALSCRATCH'] = paths['SCRATCH']
paths['SHAREDSCRATCH'] = os.getenv('SHAREDSCRATCH')
if not os.getenv('SHAREDSCRATCH'):
    paths['SHAREDSCRATCH'] = paths['SCRATCH']



# SATOPS is the default intermediate and ancillary data location.
paths['SATOPS'] = os.getenv('SATOPS')
if not os.getenv('SATOPS'):
    paths['SATOPS'] = os.path.join(os.getenv('GEOIPS_OUTDIRS'),'satops')

paths['STANDALONE_GEOIPS'] = os.getenv('STANDALONE_GEOIPS')
if not os.getenv('STANDALONE_GEOIPS'):
    paths['STANDALONE_GEOIPS'] = paths['GEOIPS']

paths['EXTERNAL_GEOIPS'] = os.getenv('EXTERNAL_GEOIPS')
if not os.getenv('EXTERNAL_GEOIPS'):
    paths['EXTERNAL_GEOIPS'] = ''

paths['LOGDIR'] = os.getenv('LOGDIR')
if not os.getenv('LOGDIR'):
    paths['LOGDIR'] = os.path.join(paths['GEOIPS_OUTDIRS'],'logs')


paths['GEOIPSTEMP'] = os.getenv('GEOIPSTEMP')
if not os.getenv('GEOIPSTEMP'):
    paths['GEOIPSTEMP'] = os.path.join(paths['SATOPS'],'intermediate_files','GeoIPStemp')
paths['GEOIPSFINAL'] = os.getenv('GEOIPSFINAL')
if not os.getenv('GEOIPSFINAL'):
    paths['GEOIPSFINAL'] = os.path.join(paths['SATOPS'],'intermediate_files','GeoIPSfinal')


# NOTE THIS IS NOT A LIST
paths['AUTOGEN_DYNAMIC_SECTORFILEPATH'] = os.path.join(paths['SATOPS'],'longterm_files','sectorfiles','dynamic')

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
    paths[paths_varname] = [os.path.join(paths['GEOIPS'],subdirs[paths_varname])]

    # Default to STANDALONE_GEOIPS if defined in bashrc
    if standalone_geoips:
        paths[paths_varname] = [os.path.join(paths['STANDALONE_GEOIPS'],subdirs[paths_varname])]

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
                paths['STATIC_SECTORFILEPATHS'] += [os.path.join(path,static_subdir)]
                paths['TEMPLATEPATHS'] += [os.path.join(path,dynamic_subdir)]
                paths['TC_TEMPLATEFILE'] += [os.path.join(path,dynamic_subdir,tctemplate)]
                paths['VOLCANO_TEMPLATEFILE'] += [os.path.join(path,dynamic_subdir,volcanotemplate)]
    # If EXTERNAL_GEOIPS is defined, use the appropriate relative path there
    # But ONLY if ext_envvar is not set (ext_envvar OVERRIDES).
    elif extgeoips:
        for path in extgeoips.split(':'):
            extgeoipspath = os.path.join(path,subdirs[paths_varname])
            #print 'EXTERNAL_GEOIPS path '+extgeoipspath
            if os.path.isdir(extgeoipspath) and extgeoipspath not in paths[paths_varname]:
                paths[paths_varname] += [extgeoipspath]
    else:
        #print 'DEFAULT '+envvar+' GEOIPS path '+str(paths[paths_varname])
        pass
