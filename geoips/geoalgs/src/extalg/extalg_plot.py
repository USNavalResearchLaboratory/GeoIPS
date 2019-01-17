#!/bin/env python
import os

# Installed Libraries
from IPython import embed as shell
import logging
from matplotlib import cm, colors
import numpy as np

# GeoIPS Libraries
from geoips.utils.normalize import normalize
from geoips.utils.gencolormap import get_cmap

log = logging.getLogger(__name__)

def write_winds(gi):
    fn = gi.get_filename(imgkey='winds')
    fn.ext = 'txt'

    log.info('Writing wind output text file: '+fn.name)

    # Only get unmasked values
    indxs = np.ma.where(gi.image['winds'])

    speeds = gi.image['speed'][indxs]
    dirs = gi.image['dir'][indxs]
    lats = gi.image['lats'][indxs]
    lons = gi.image['lons'][indxs]

    fn.makedirs()
    fp1 = open(fn.name, 'w')

    from datetime import datetime, timedelta
    dt1a = datetime.utcnow()
    fp1.write('speed dir lat lon')
    fp1.writelines([str(speed)+' '+str(lat)+' '+str(lon)+'\n' for (speed, dir, lat, lon) in iter(zip(speeds, dirs, lats, lons))])
    dt1b = datetime.utcnow()
    time1 = dt1b-dt1a
    log.info('Time to write text file: '+str(time1))

    # Might be better with very large arrays so entire thing is not in memory.
    #from itertools import izip
    #for (speed, dir, lat, lon) in izip(speeds, dirs, lats, lons):
    #   fp2.write(str(speed)+' '+str(dir)+' '+str(lat)+' '+str(lon)+'\n')

def extalg_plot(gi, imgkey=None):

    # Figure and axes
    gi._figure, gi._axes = gi._create_fig_and_ax()

    if imgkey:
        # Can specify different methods for different image types
        # Note I didn't specify a 'winds' output image currently, 
        # but we could...
        if imgkey == 'winds' and gi.is_final:
            write_winds(gi)
        colormapper = cm.ScalarMappable(norm=colors.NoNorm(), cmap=get_cmap(gi.product.cmap))
        if 'float' in str(gi.image[imgkey].dtype):
            pass
        else:
            gi.image[imgkey].dtype = 'float64'
        currimg = colormapper.to_rgba(normalize(gi.image[imgkey]))
        gi.basemap.imshow(currimg, ax=gi.axes, interpolation='nearest')
    else:
        colormapper = cm.ScalarMappable(norm=colors.NoNorm(), cmap=get_cmap(gi.product.cmap))
        if 'float' in str(gi.image.dtype):
            pass
        else:
            gi.image.dtype = 'float64'
        currimg = colormapper.to_rgba(normalize(gi.image))
        gi.basemap.imshow(currimg, ax=gi.axes, interpolation='nearest')

    if gi.is_final:
        gi.finalize()
