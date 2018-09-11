#!/bin/env python
import os
import logging
from datetime import timedelta

log = logging.getLogger(__name__)

def winds(datafile, sector, product, workdir):
    '''
    This method creates image output for arbitrary wind
    vector data.

    It will overlay on related geostationary imagery
    i alg_platform and alg_source are included in 
    the metadata of the scifile object.

    Datasets must be named include '1d' in order for 
    this to plot.
    '''
    outdata = {}

    from geoips.scifile.utils import find_datafiles_in_range
    from geoips.scifile.scifile import SciFile
    matching_files = find_datafiles_in_range(sector,
        datafile.metadata['top']['alg_platform'].lower(),
        datafile.metadata['top']['alg_source'].lower(),
        datafile.start_datetime - timedelta(minutes=60),
        datafile.start_datetime - timedelta(minutes=0),
        )
    if matching_files:
        matching_file = SciFile()
        matching_file.import_data([matching_files[-1]])


    for dsname in datafile.datasets.keys():
        #if '1d' not in dsname or '800' not in dsname:
        if '1d' not in dsname:
            continue
        outdata[dsname] = {}

        if matching_files:
            #outdata[dsname]['BACKGROUND'] = matching_file.variables[datafile.metadata['ds'][dsname]['alg_channel']]
            outdata[dsname]['BACKGROUND'] = matching_file
        #for varname in datafile.datasets[dsname].variables.keys():
        #    outdata[dsname][varname] = datafile.datasets[dsname].variables[varname]
        outdata[dsname]['datafile'] = datafile

    return outdata, None
