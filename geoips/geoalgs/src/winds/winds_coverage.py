#!/bin/env python
import os

# Installed Libraries
from IPython import embed as shell
import logging
import numpy as np

log = logging.getLogger(__name__)

def winds_coverage(gi, imgkey=None):
    '''
    I think this is overkill - it should either take
    imgkey, or not.  I think it loops through keys in 
    process. But perhaps it should not loop through in
    process, have to think about this.
    Or maybe it should loop in process - different coverage for each 
    different data array in the dictionary...
    '''
    return 100
         
