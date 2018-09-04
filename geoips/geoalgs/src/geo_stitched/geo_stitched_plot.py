#!/bin/env python
import os

# Installed Libraries
import logging
from matplotlib import cm, colors
import numpy as np
from scipy.interpolate import griddata
from datetime import datetime

# GeoIPS Libraries
from geoips.utils.normalize import normalize
from geoips.utils.gencolormap import get_cmap

log = logging.getLogger(__name__)


def set_plotting_params(gi, speed=None, platform=None, source=None, prodname=None, bgname=None, start_dt=None, end_dt=None):

    gi.set_geoimg_attrs(platform, source, prodname, bgname, start_dt=start_dt, end_dt=end_dt)

    if speed is not None:
        from matplotlib.colors import Normalize
        cmap = 'tropix_no_white'
        if gi.product.cmap:
            cmap = gi.product.cmap

        norm = Normalize(vmin = speed.min(), vmax= speed.max())
        ticks = [int(speed.min()), int(speed.max())]
        ticklabels = ticks
        #if gi.product.colorbarsticks:

        gi.set_colorbars(cmap, ticks, ticklabels=ticklabels, title=None, bounds=None, norm=norm)

    else:
        gi._colorbars = []

    # Figure and axes
    gi._figure, gi._axes = gi._create_fig_and_ax()

def find_var(gi, varname):
    for key in gi.image.keys():
        if varname in gi.image[key].variables.keys():
            return gi.image[key].variables[varname]

def geo_stitched_plot(gi, imgkey=None):

    if not imgkey:
        return

    if 'Infrared' in imgkey:
        fg = gi.image[imgkey]
    elif 'Visible' in imgkey:
        fg = gi.image[imgkey]

    log.info('Setting up fig and ax for dataset: %s'%(imgkey))
    set_plotting_params(gi, speed=None, platform=None, source=None,
                prodname=imgkey, bgname=None,
                start_dt=None, end_dt=None)

    log.info('Plotting imgkey: %s'%(imgkey))

    gi.basemap.imshow(fg,ax=gi.axes,cmap=get_cmap('Greys_r'), interpolation='nearest')

    if gi.is_final:
        gi.finalize()


