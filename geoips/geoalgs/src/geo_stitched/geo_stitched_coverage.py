#!/bin/env python
import os

# Installed Libraries
import logging
import numpy as np

log = logging.getLogger(__name__)

def geo_stitched_coverage(gi, imgkey=None):
    '''
    utils/path/productfilename.py passes imgkey to geoimgobj.coverage() if 
    imgkey defined, and process.py loops through imgkeys just before 
    doing the final plotting to get the actual coverage 
    '''
    log.info('Running geo_stitched_coverage for %s'%imgkey)
    if imgkey:
        return (np.ma.count(gi[imgkey])*1.0 / gi[imgkey].size)*100

    if imgkey is None:
        return 101
    return 102
    #for imgkey in gi:
    #    return (np.ma.count_masked(gi[imgkey].variables['BACKGROUND'])*1.0 / np.ma.count_masked(gi[imgkey].variables['direction']))*100
         
