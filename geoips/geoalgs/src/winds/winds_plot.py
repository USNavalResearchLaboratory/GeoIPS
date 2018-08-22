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

    # Figure and axes
    gi._figure, gi._axes = gi._create_fig_and_ax()

    log.info('Plotting dataset: %s'%(imgkey))

    df = gi.image[imgkey]['datafile']
    ds = df.datasets[imgkey]
    if 'BACKGROUND' in gi.image[imgkey]:
        bgfile = gi.image[imgkey]['BACKGROUND']

    if '1d' in imgkey:
        speed = ds.variables['speed']
        u = speed * np.cos(np.radians(ds.variables['direction']))
        v = speed * np.sin(np.radians(ds.variables['direction']))
        pres = ds.variables['pres']
        lats = ds.variables['lats']
        lons = ds.variables['lons']
        alg_channel = 'None' 
        alg_info = imgkey
        if 'BACKGROUND' in gi.image[imgkey]:
            alg_channel = df.metadata['ds'][imgkey]['alg_channel']
            bgvar = bgfile.variables[alg_channel]
            bgvar.mask = bgfile.geolocation_variables['Latitude'].mask
            gi.basemap.imshow(bgvar,ax=gi.axes,cmap=get_cmap('Greys'))
        gi.basemap.barbs(lons.data,lats.data,u,v,speed,ax=gi.axes,cmap=get_cmap('tropix_no_white'))

        from geoimg.title import Title
        gi._title = Title.from_objects(gi.datafile, gi.sector, gi.product, extra_lines = ['Using: '+alg_info, 'Plotted over: '+alg_channel])
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
