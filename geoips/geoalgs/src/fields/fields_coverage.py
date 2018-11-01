#!/bin/env python
import os

# Installed Libraries
import logging
import numpy as np

log = logging.getLogger(__name__)

def fields_coverage(gi, imgkey=None):
    '''
    utils/path/productfilename.py passes imgkey to geoimgobj.coverage() if 
    imgkey defined, and process.py loops through imgkeys just before 
    doing the final plotting to get the actual coverage 
    '''
    log.info('Running fields_coverage for %s'%imgkey)
    #if imgkey:
    #    parts = imgkey.split('_',3)
    #    varname = parts[0]
    #    if 'fieldsdata' in imgkey:
    #        barbsds = gi[imgkey][0]
    #        return (np.ma.count(barbsds.variables['direction'])*1.0 / barbsds.variables['direction'].size)*100
    #    elif 'magspeed' in gi[imgkey].variables.keys():
    #        return (np.ma.count(gi[imgkey].variables['magspeed'])*1.0 / gi[imgkey].variables['magspeed'].size)*100
    #    elif 'image1' in gi[imgkey].variables.keys():
    #        return (np.ma.count(gi[imgkey].variables['image1'])*1.0 / gi[imgkey].variables['image1'].size)*100
    #    elif 'image2' in gi[imgkey].variables.keys():
    #        return (np.ma.count(gi[imgkey].variables['image2'])*1.0 / gi[imgkey].variables['image2'].size)*100
    #    elif 'image12' in gi[imgkey].variables.keys():
    #        return (np.ma.count(gi[imgkey].variables['image12'])*1.0 / gi[imgkey].variables['image12'].size)*100
    #    elif 'image21' in gi[imgkey].variables.keys():
    #        return (np.ma.count(gi[imgkey].variables['image21'])*1.0 / gi[imgkey].variables['image21'].size)*100
    #    elif 'barbs' in varname.lower():
    #        return (np.ma.count(gi[imgkey].variables['direction'])*1.0 / gi[imgkey].variables['direction'].size)*100
    #    elif 'heights' in varname.lower():
    #        return (np.ma.count(gi[imgkey].variables['pressure'])*1.0 / gi[imgkey].variables['pressure'].size)*100

    if imgkey is None:
        return 101
    return 102
    #for imgkey in gi:
    #    return (np.ma.count_masked(gi[imgkey].variables['BACKGROUND'])*1.0 / np.ma.count_masked(gi[imgkey].variables['direction']))*100
         
