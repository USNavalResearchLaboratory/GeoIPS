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


def set_plotting_params(gi, speed=None, platform=None, source=None, prodname=None, bgname=None, start_dt=None, end_dt=None):

    gi.set_geoimg_attrs(platform, source, prodname, bgname, start_dt=start_dt, end_dt=end_dt)

    if speed is not None:
        from matplotlib.colors import Normalize
        cmap = 'tropix_no_white'
        if gi.product.cmap:
            cmap = gi.product.cmap

        if not np.ma.is_masked(speed.min()):
            norm = Normalize(vmin = speed.min(), vmax= speed.max())
            ticks = [int(speed.min()), int(speed.max())]
            ticklabels = ticks
        else:
            norm = None
            ticks = None
            ticklabels = None
        #if gi.product.colorbarsticks:

        gi.set_colorbars(cmap, ticks, ticklabels=ticklabels, title=None, bounds=None, norm=norm)

    else:
        gi._colorbars = []

    # Figure and axes
    gi._figure, gi._axes = gi._create_fig_and_ax()

def extalg_plot(gi, imgkey=None):

    gi.set_plotting_params(gi)

    if imgkey and imgkey == 'rainrate':

        colormapper = cm.ScalarMappable(norm=colors.NoNorm(), cmap=get_cmap('frozen_cmap'))
        currimg = colormapper.to_rgba(normalize(gi.image['rainrate']['frozen']))
        # imshow expects upside down arrays, but we should not store them upside down
        # so flipud here
        gi.basemap.imshow(np.flipud(gi.image['rainrate']['frozen']))

        colormapper = cm.ScalarMappable(norm=colors.NoNorm(), cmap=get_cmap('liquid_cmap'))
        currimg = colormapper.to_rgba(normalize(gi.image['rainrate']['liquid']))
        # imshow expects upside down arrays, but we should not store them upside down
        # so flipud here
        gi.basemap.imshow(np.flipud(gi.image['rainrate']['liquid']))

        ##if 'float' in str(gi.image[imgkey].dtype):
        ##    pass
        ##else:
        ##    gi.image[imgkey].dtype = 'float64'
        ##gi.basemap.imshow(np.flipud(currimg), ax=gi.axes, interpolation='nearest')


    if gi.is_final:
        gi.finalize()
