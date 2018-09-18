#!/bin/env python
import os

# Installed Libraries
from IPython import embed as shell
import logging
import numpy as np

log = logging.getLogger(__name__)

def extalg_coverage(gi, imgkey=None):
    '''
    I think this is overkill - it should either take
    imgkey, or not.  I think it loops through keys in 
    process. But perhaps it should not loop through in
    process, have to think about this.
    Or maybe it should loop in process - different coverage for each 
    different data array in the dictionary...
    '''
    
    if imgkey and imgkey == 'rainrate':
        return 100 * (float(np.ma.count(gi[imgkey]['frozen'])) / gi[imgkey]['frozen'].size)
    else:
        return 101
         
