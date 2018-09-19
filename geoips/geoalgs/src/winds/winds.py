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
    log.info('Trying to find matching background imagery: %s %s %s to %s from %s'%
                (   datafile.metadata['top']['alg_platform'],
                    datafile.metadata['top']['alg_source'],
                    datafile.start_datetime - timedelta(minutes=60),
                    datafile.start_datetime + timedelta(minutes=5),
                    'nesdisstar',
            ))
    matching_files = find_datafiles_in_range(sector,
        datafile.metadata['top']['alg_platform'],
        datafile.metadata['top']['alg_source'],
        datafile.start_datetime - timedelta(minutes=60),
        datafile.start_datetime + timedelta(minutes=5),
        dataprovider='*',
        )
    if matching_files:
        log.info('Found matching files:\n%s\nUsing: %s'%
                ('\n        '.join(matching_files),
                matching_files[-1],
                ))
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
