#!/bin/env python

import os
from geoips.utils.plugin_paths import paths as gpaths


def get_geolocation_filename(sensor, prefix, metadata, sect=None):
    '''
    Produces a file name for a temporary geolocation data file.
    The path to the file is specified by `path`.
    The file prefix is specified by `prefix` and can be anything.
    The remainder of the file name is constructed using hashes of:
        1) The input sector's `area_dict` attribute.
        2) The input metadata dictionary.
    Use of hashes in this way should create completely unique filenames any time either a sector
    change or a satellite's geolocation metadata changes.
    '''
    sensor = metadata['sensor']

    if sect:
        print frozenset(sect.area_definition.proj_dict.items())
        sect_hash = hash(frozenset(sect.area_definition.proj_dict.items()))
    else:
        sect_hash = 'None'
    md_hash = hash(frozenset(metadata))

    fname = '{}_{}_{}.dat'.format(prefix, sect_hash, md_hash)

    # Check read-only directories
    # Return if it exists
    if os.getenv('READ_GEOLOCDIRS'):
        read_geolocdirs = [pp+'/AHI' for pp in os.getenv('READ_GEOLOCDIRS').split(':')]
    else:
        read_geolocdirs = []
    for dirname in read_geolocdirs:
        if os.path.exists(os.path.join(dirname, fname)):
            return os.path.join(dirname, fname)

    # Return filename in read/write directories
    if sect and sect.isdynamic:
        if os.getenv('DYNAMIC_GEOLOCDIR'):
            dirname = os.path.join(os.getenv('DYNAMIC_GEOLOCDIRS'), sensor)
        else:
            dirname = os.path.join(gpaths['SATOPS'], 'intermediate_files', 'geolocation', sensor)
    else:
        if os.getenv('GEOLOCDIR'):
            dirname = os.path.join(os.getenv('DYNAMIC_GEOLOCDIRS'), sensor)
        else:
            dirname = os.path.join(gpaths['SATOPS'], 'intermediate_files', 'geolocation', sensor)
    return os.path.join(dirname, fname)



