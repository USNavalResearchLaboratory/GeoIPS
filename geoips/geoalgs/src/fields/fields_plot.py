#!/bin/env python

# Installed Libraries
import logging
from matplotlib import cm, colors
import numpy as np

# GeoIPS Libraries
from geoips.utils.normalize import normalize
from .winds_plot import set_winds_plotting_params
from geoips.utils.gencolormap import get_cmap
from .winds_utils import thin_arrays, uv2spd

log = logging.getLogger(__name__)

prodnames = {'dwptdp': 'Dew_Point_Depression',
             'vpress': 'Vapor_Pressure',
             'pottmp': 'Potential_Temperature',
             'av':     'Absolute_Vorticity',
             'cmr':    'Cloud_Mixing_Ratio',
             'geoph':  'Geopotential_Height',
             'rh':     'Relative_Humidity',
             'temp':   'Temperature',
             'uwind':  'U_Component_of_Wind',
             'vwind':  'V_Component_of_Wind',
             'vv':     'Vertical_Velocity',
             'Winds':     'Winds',
             }


def fields_plot(gi, imgkey=None):

    if not imgkey:
        return
    varname, lev, sectname = imgkey.split('_')
    prod_display_name = varname
    if varname in prodnames.keys():
        prod_display_name = prodnames[varname]
    prodname = '{0} at {1} mb'.format(prod_display_name, lev)
    bgname = None
    dataset = gi.image[imgkey]
    
    if varname == 'Winds':
        log.info('Setting up fig and ax for dataset: %s with bgname: %s' % (prodname, bgname))
        u_kts = dataset.variables['uwind'+lev]
        v_kts = dataset.variables['vwind'+lev]
        numvecs = np.ma.count(u_kts)
        maxvecs = 4000
        speed_kts, direc_deg = uv2spd(u_kts, v_kts)
        lons = dataset.geolocation_variables['Longitude']
        lats = dataset.geolocation_variables['Latitude']
        [u_kts, v_kts, lats, lons, speed_kts] = thin_arrays(numvecs, max_points=maxvecs,
                                                            arrs=[u_kts, v_kts, lats, lons, speed_kts])
        set_winds_plotting_params(gi, speed_kts, pressure=None, altitude=None,
                                  platform=dataset.platform_name, source=dataset.source_name,
                                  prodname=prodname, bgname=bgname,
                                  start_dt=dataset.start_datetime, end_dt=dataset.end_datetime,
                                  ticks_vals=None, listed_colormap_vals=None)
        gi.basemap.barbs(lons.data, lats.data,
                         u_kts, v_kts, speed_kts,
                         ax=gi.axes,
                         cmap=gi.colorbars[0].cmap,
                         sizes=dict(height=1, spacing=0.5),
                         norm=gi.colorbars[0].norm,
                         linewidth=0.5,
                         length=5,
                         latlon=True)
    else:
        set_winds_plotting_params(gi, speed=None, pressure=None, altitude=None,
                                  platform=dataset.platform_name, source=dataset.source_name,
                                  prodname=prodname, bgname=bgname,
                                  start_dt=dataset.start_datetime, end_dt=dataset.end_datetime,
                                  ticks_vals=None, listed_colormap_vals=None)
        cmapname = 'tropix_no_white'
        plotdata = dataset.variables[varname+lev]
        colormapper = cm.ScalarMappable(norm=colors.NoNorm(), cmap=get_cmap(cmapname))
        currimg = colormapper.to_rgba(normalize(plotdata))
        # imshow expects upside down arrays
        gi.basemap.imshow(np.flipud(currimg), ax=gi.axes, interpolation='nearest')

    if gi.is_final:
        gi.finalize()


