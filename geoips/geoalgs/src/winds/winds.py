#!/bin/env python
import os
import logging
from IPython import embed as shell

log = logging.getLogger(__name__)

def winds(datafile, sector, product, workdir):
    '''
    This is a template for creating an external algorithm for operating on 
    arbitrary data types from the datafile (registered, sectored, 
    pre-registered...), and returning arbitrary arrays.  There must be a 
        geoalgs/src/extalg/extalg_plot.py
        geoalgs/src/extalg/extalg_coverage.py
    to go with 
        geoalgs/src/extalg/extalg.py
    so the plotting and coverage checking routines know how to handle the
    arbitrary arrays. 

    Oh, we should probably have a default plot / coverage routine in 
        geoimg/plot/extalg.py, so it uses that if extalg_plot.py and
        extalg_coverage.py are not defined ?

    This is a pretty useless function, but should hopefully provide a 
        template for more useful applications.
    '''

    '''
    Here is your arbitrary outdata dictionary!!!
    You can put anything you want in here !!!!
    Then tell <extalg>_plot how to plot each entry, 
    and <extalg>_coverage how to check coverage for
    each entry!!!!
    '''
    outdata = {}
    for dsname in datafile.datasets.keys():
        #if '1d' not in dsname or '800' not in dsname:
        if '1d' not in dsname:
            continue
        outdata[dsname] = {}
        for varname in datafile.datasets[dsname].variables.keys():
            outdata[dsname][varname] = datafile.datasets[dsname].variables[varname]

    return outdata, None
