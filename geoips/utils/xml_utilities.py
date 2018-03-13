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


#Python Standard Libraries
import os
import errno
import logging
import commands
import filecmp

#Installed Libraries
from lxml import etree, objectify
from IPython import embed as shell


# GeoIPS Libraries
from .decorators import retry
from .plugin_paths import paths
from .log_setup import interactive_log_setup

log = interactive_log_setup(logging.getLogger(__name__))


class DTDError(Exception):
    def __init__(self, msg):
        self.value = msg
    def __str__(self):
        return self.value

class DTDMissing(Exception):
    def __init__(self, msg):
        self.value = msg
    def __str__(self):
        return self.value

def read_xmlfile(path, do_objectify=True):
    '''Read an XML file and return the resulting object.  If the
    objectify keyword is set, the return value will be an objectified
    ElementTree object, otherwise, it will simply be an ElementTree
    object.'''
    if do_objectify is False:
        log.debug('  Reading xml file, no do_objectify: '+path)
        parser = etree.XMLParser(dtd_validation=True, attribute_defaults=True)
        xmlfile = etree.parse(path, parser)
    else:
        parser = objectify.makeparser(dtd_validation=True, attribute_defaults=True)
        log.debug('  Reading xml file, do_objectify: '+path)

        try:
            xmlfile = objectify.parse(path, parser)

        # Handle syntax errors (includes missing DTD)
        except etree.XMLSyntaxError, resp:
            # Attempt to read file without performing DTD validation
            parser = objectify.makeparser(dtd_validation=False, attribute_defaults=False)

            # If this raises an error, we have a non-validation related problem, so let it be raised normally
            try:
                xmlfile = objectify.parse(path, parser)
            except:
                log.error('Failed on objectify.parse for file '+path)
                raise

            # Get the path to the requested DTD
            dtd_path = xmlfile.docinfo.system_url
            # Make sure we have an absolute path to this file
            if not os.path.isabs(dtd_path):
                dtd_path = '{}/{}'.format(os.path.dirname(path), dtd_path)

            # Path to default DTD file. Need to differentiate between sectorfiles.dtd and productfiles.dtd!
            # Also need to use STANDALONE_GEOIPS, not GEOIPS.  STANDALONE_GEOIPS defaults to GEOIPS if
            # it is not set in the environment.  We may want to try GEOIPS first, though?  What if we
            # create our own dtd in separate repos ?
            realdtd = '{}/geoips/sectorfiles/sectorfiles.dtd'.format(paths['STANDALONE_GEOIPS'])
            if 'productfiles' in dtd_path:
                realdtd = '{}/geoips/productfiles/productfiles.dtd'.format(paths['STANDALONE_GEOIPS'])

            # For dynamic sectorfile DTD files
            # If the DTD is in AUTOGEN_DYNAMIC_SECTORFILEPATH:
            #   Delete it if it exists
            if os.path.dirname(dtd_path) == paths['AUTOGEN_DYNAMIC_SECTORFILEPATH']:
                if os.path.isfile(dtd_path):
                    os.unlink(dtd_path)

            # If the DTD is a broken symlink, then delete it
            try:
                os.stat(dtd_path)
            except OSError, e:
                if e.errno == errno.ENOENT:
                    try:
                        os.unlink(dtd_path)
                    except OSError, e2:
                        if e2.errno == errno.ENOENT:
                            pass
                else:
                    raise

            # If the DTD doesn't exist, then link to the default DTD
            if not os.path.isfile(dtd_path):
                try:
                    log.interactive('DTD not found.  Linking DTD: {} => {}'.format(dtd_path, realdtd))
                    if os.path.isfile(realdtd):
                        os.symlink(realdtd, dtd_path)
                    else:
                        raise OSError('No such file: {}'.format(realdtd))
                # Ignore errors if the file exists.  Someone else must have created it for us here.
                except OSError, e:
                    if not e.errno == errno.EEXIST:
                        raise
                # Attempt to read again
                return read_xmlfile(path, do_objectify)

            log.error('Failed on read_xmlfile for file '+path)
            raise resp

    return xmlfile


def get_sector_desig(sector=None, continent=None, country='x', area='x', subarea='x', state='x', city='x',time=None):
    '''Build the sector designation string from the NAME element
    in a sector XML element from etree or provided keywords.'''
    #Build area name dict and replace empty values with 'x'
    if sector is not None:
        name_info = sector.tree.find('NAME')
        desig = '-'.join([child.text if child.text else 'x' for child in name_info.iterchildren()])
        if (sector.time is not ''):
            desig = desig+'_'+sector.time
    else:
        parts = [continent, country, area, subarea, state, city]
        for ind, part in enumerate(parts):
            if not part:
                parts[ind] = 'x'
            
        if continent is not None:
            desig = '-'.join(parts)
            if (time is not None):
                desig = desig+'_'+time
        else:
            raise TypeError('Either sector or (at a minimum) continent must be provided.')
    return desig
