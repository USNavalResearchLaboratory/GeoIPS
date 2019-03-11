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
        try:
            lev = int(varname[-4:])
        except ValueError:
            continue
        prodname = varname[:-4]
        #finaldata['{0}_{1:04d}_{2}'.format(prodname, lev, sector.name)] = ds
        #if 'uwind' in varname:
        #    finaldata['Winds_{0:04d}_{1}'.format(lev, sector.name)] = ds

    return finaldata, None
            
