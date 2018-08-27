#!/bin/env python
import os

# Installed Libraries
import logging
from matplotlib import cm, colors
import numpy as np
from scipy.interpolate import griddata

# GeoIPS Libraries
from geoips.utils.normalize import normalize
from geoips.utils.gencolormap import get_cmap

log = logging.getLogger(__name__)


def winds_plot(gi, imgkey=None):


    df = gi.image[imgkey]['datafile']
    ds = df.datasets[imgkey]

    bgname = 'None' 
    prodname = imgkey
    if 'BACKGROUND' in gi.image[imgkey]:
        bgfile = gi.image[imgkey]['BACKGROUND']
        bgname = df.metadata['ds'][imgkey]['alg_channel']
        bgvar = np.flipud(bgfile.variables[bgname])

    log.info('Setting up fig and ax for dataset: %s with bgname: %s'%(prodname, bgname))

    new_platform = gi.datafile.metadata['top']['alg_platform'].lower() 
    new_source = gi.datafile.metadata['top']['alg_source'].lower() 


    log.info('Plotting dataset: %s'%(imgkey))

    if '1d' in imgkey:
        resolution = min(gi.sector.area_info.proj4_pixel_width, gi.sector.area_info.proj4_pixel_height)
        direction = ds.variables['direction']
        speed = ds.variables['speed']
        u = speed * np.cos(np.radians(direction))
        v = speed * np.sin(np.radians(direction))
        pres = ds.variables['pres']
        lats = ds.variables['lats']
        lons = ds.variables['lons']

        from geoips.geoalgs.lib.motion_plot import downsample_winds
        from geoips.geoalgs.lib.motion_plot import set_winds_plotting_params

        lonsthin, latsthin, uthin, vthin, speedthin, directionthin = downsample_winds(resolution, lons, lats, u, v, speed, direction)
        set_winds_plotting_params(gi, speedthin, new_platform, new_source, prodname, bgname)

        if 'BACKGROUND' in gi.image[imgkey]:
            gi.basemap.imshow(bgvar,ax=gi.axes,cmap=get_cmap('Greys'))
        gi.basemap.barbs(lonsthin.data,latsthin.data,
                        uthin,vthin,speedthin,
                        ax=gi.axes,
                        cmap=get_cmap('tropix_no_white'),
                        sizes=dict(height=0.8, spacing=0.3),
                        linewidth=2,
                        length=5,
                        latlon=True)


    #elif 'grid' in imgkey:
    #    speed = gi.image[imgkey]['gridspeed']
    #    u = gi.image[imgkey]['gridu']
    #    v = gi.image[imgkey]['gridv']
    #    pres = gi.image[imgkey]['gridpres']
    #    lats = gi.datafile.datasets[imgkey].geolocation_variables['Latitude']
    #    lons = gi.datafile.datasets[imgkey].geolocation_variables['Longitude']
    #    #x,y = gi.basemap(lons,lats)
    #    # transform from spherical to map projection coordinates (rotation
    #    # and interpolation).
    #    nxv = 100; nyv =100 
    #    # Can't pass masked lat/lon to transform
    #    # Don't know why lats[:0] and lons[0:] don't work ...?
    #    log.info('Interpolating u, v, pressure to basemap grid')
    #    udat, vdat, xv, yv = gi.basemap.transform_vector(u,v,lons.data[0],np.flipud(lats.data).T[0],nxv,nyv,returnxy=True)
    #    speeddat, xspd, yspd = gi.basemap.transform_scalar(speed,lons.data[0],np.flipud(lats.data).T[0],nxv,nyv,returnxy=True)
    #    presdat, xpres, ypres = gi.basemap.transform_scalar(pres,lons.data[0],np.flipud(lats.data).T[0],nxv,nyv,returnxy=True)
    #    cmap = 'tropix_no_white'
    #    # Can't pass masked lat/lon/speed to barbs
    #    log.info('Plotting barbs')
    #    gi.basemap.barbs(xv, yv, udat, vdat, speeddat, ax=gi.axes, cmap=get_cmap(cmap))
    #    #log.info('Plotting contour')
    #    #gi.basemap.contour(xpres, ypres, presdat, ax=gi.axes, interpolation='nearest')
    else:
        return
        #speed = gi.image['gridspeed']
        #u = gi.image['gridu']
        #v = gi.image['gridv']
        #pres = gi.image['gridpres']
        #lats = gi.datafile.datasets.keys()[0].geolocation_variables['Latitude']
        #lons = gi.datafile.datasets.keys()[0].geolocation_variables['Longitude']


    if gi.is_final:
        gi.finalize()
