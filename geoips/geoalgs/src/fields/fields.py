#!/bin/env python
import logging

log = logging.getLogger(__name__)


def fields(datafile, sector, product, workdir):
    '''
    '''
    if sector.name not in datafile.datasets.keys():
        return [], None

    ds = datafile.datasets[sector.name]

    finaldata = {}
    for varname in ds.variables.keys():
        finaldata['{0}_{1}'.format(varname, sector.name)] = datafile
        if 'uwind' in varname:
            lev = int(varname[-4:])
            finaldata['Winds_{0:d}_{1}'.format(lev, sector.name)] = datafile

    return finaldata, None
            
