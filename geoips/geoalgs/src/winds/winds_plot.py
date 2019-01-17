#!/bin/env python
import os

# Installed Libraries
import logging
from matplotlib import cm, colors
import numpy as np
from scipy.interpolate import griddata
import re

# GeoIPS Libraries
from geoips.utils.normalize import normalize
from geoips.utils.gencolormap import get_cmap

log = logging.getLogger(__name__)


def winds_plot(gi, imgkey=None):


    df = gi.image[imgkey]['datafile']
    ds = df.datasets[imgkey]

    bgname = 'None' 
    prodname = imgkey
    day_percent = None
    if 'BACKGROUND' in gi.image[imgkey]:
        bgfile = gi.image[imgkey]['BACKGROUND']
        bgvarname = df.metadata['ds'][imgkey]['alg_channel']
        bgvar = np.flipud(bgfile.variables[bgvarname])
        lats = bgfile.geolocation_variables['Latitude']
        lons = bgfile.geolocation_variables['Longitude']
        sunzen = bgfile.geolocation_variables['SunZenith']
        from .motion_config import motion_config
        from .EnhancedImage import EnhancedImage
        if bgvar.name not in motion_config(bgfile.source_name).keys():
            log.warning('Variable %s not defined in motion_config for %s, can not find background, not plotting'%
				(bgvar.name, bgfile.source_name))
            return
        config = motion_config(bgfile.source_name)[bgvar.name]
        bgcmap = 'Greys'
        if 'plot_params' in config.keys() \
            and 'EnhImage' in config['plot_params'].keys() \
            and 'cmap' in config['plot_params']['EnhImage'].keys():
            bgcmap = config['plot_params']['EnhImage']['cmap']

        enhdata = EnhancedImage(
            bgvar,
            bgvar.shape,
            lats,
            lons,
            sunzen=sunzen,
            )
        enhdata.enhanceImage(config)
        bgvar = enhdata.Data

        chanstr = re.sub(r"^B","Channel ",bgvarname).replace('BT',' BT').replace('Ref',' Reflectance')
        if bgvar.wavelength:
            bgname = '%s - %s, %s um'%(bgvar.platform_name, chanstr, bgvar.wavelength)
        else:
            bgname = '%s - %s'%(bgvar.platform_name, chanstr)
        if np.ma.count(bgvar):
            try:
                day_percent = (1.0 * np.ma.count(bgvar[ds.day_inds]) / np.ma.count(bgvar)) * 100
            except KeyError:
                pass

    if gi.datafile.dataprovider is not None:
        prodname = prodname+', '+gi.datafile.dataprovider
    if day_percent is not None:
        prodname = '%s Product: %d'%(prodname, day_percent) + '% day'
    prodname = prodname.replace('_',' ')

    log.info('Setting up fig and ax for dataset: %s with bgname: %s'%(prodname, bgname))

    new_platform = gi.datafile.metadata['top']['alg_platform']
    new_source = gi.datafile.metadata['top']['alg_source']

    log.info('Plotting dataset: %s'%(imgkey))

    resolution = min(gi.sector.area_info.proj4_pixel_width, gi.sector.area_info.proj4_pixel_height)
    direction = ds.variables['direction']
    speed = ds.variables['speed']
    u = speed * np.cos(np.radians(direction))
    v = speed * np.sin(np.radians(direction))
    pres = ds.variables['pres']
    lats = ds.variables['lats']
    lons = ds.variables['lons']

    from geoips.geoalgs.lib.amv_plot import downsample_winds
    from geoips.geoalgs.lib.amv_plot import set_winds_plotting_params

    set_winds_plotting_params(gi, speed, None, None, new_platform, new_source, prodname, bgname)

    if 'BACKGROUND' in gi.image[imgkey]:
        log.info('Plotting background image %s'%(bgname))
        gi.basemap.imshow(bgvar,ax=gi.axes,cmap=get_cmap(bgcmap))


    '''
    NOTE there appears to be an error in basemap - I had to add a try except to allow 
    for different outputs from np.where
    4778                 thresh = 360.-londiff_sort[-2] if nlons > 2 else 360.0 - londiff_sort[-1]
    ***4779                 try:
    ***4780                     itemindex = len(lonsin)-np.where(londiff>=thresh)[0][0]
    ***4781                 except IndexError:
    ***4782                     itemindex = len(lonsin)-np.where(londiff>=thresh)[0]
    4783             else:
    4784                 itemindex = 0
    4785
    4786             if fix_wrap_around and itemindex:
    4787                 # check to see if cyclic (wraparound) point included
    4788                 # if so, remove it.
    4789                 if np.abs(lonsin[0]-lonsin[-1]) < 1.e-4:
    4790                     hascyclic = True
    4791                     lonsin_save = lonsin.copy()
    4792                     lonsin = lonsin[1:]
    /satops/geoips_externals_nrl-2.7/built/anaconda2/lib/python2.7/site-packages/mpl_toolkits/basemap/__init__.py
    '''


    log.info('Plotting barbs with colorbars %s'%(gi.colorbars))

    gi.basemap.barbs(lons.data,lats.data,
                    u,v,speed,
                    ax=gi.axes,
                    cmap=gi.colorbars[0].cmap,
                    sizes=dict(height=0.8, spacing=0.3),
                    norm=gi.colorbars[0].norm,
                    linewidth=2,
                    length=5,
                    latlon=True)


    if gi.is_final:
        gi.finalize()
