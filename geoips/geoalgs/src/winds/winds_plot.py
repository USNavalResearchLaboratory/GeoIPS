#!/bin/env python
import os

# Installed Libraries
from IPython import embed as shell
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

    if '1d' in imgkey:
        speed = gi.image[imgkey]['speed']
        u = speed * np.cos(np.radians(gi.image[imgkey]['direction']))
        v = speed * np.sin(np.radians(gi.image[imgkey]['direction']))
        pres = gi.image[imgkey]['pres']
        lats = gi.image[imgkey]['lats']
        lons = gi.image[imgkey]['lons']
        gi.basemap.barbs(lons,lats,u,v,speed,ax=gi.axes,cmap=get_cmap('tropix_no_white'))
    elif 'grid' in imgkey:
        speed = gi.image[imgkey]['gridspeed']
        u = gi.image[imgkey]['gridu']
        v = gi.image[imgkey]['gridv']
        pres = gi.image[imgkey]['gridpres']
        lats = gi.datafile.datasets[imgkey].geolocation_variables['Latitude']
        lons = gi.datafile.datasets[imgkey].geolocation_variables['Longitude']
        #x,y = gi.basemap(lons,lats)
        # transform from spherical to map projection coordinates (rotation
        # and interpolation).
        nxv = 100; nyv =100 
        # Can't pass masked lat/lon to transform
        # Don't know why lats[:0] and lons[0:] don't work ...?
        log.info('Interpolating u, v, pressure to basemap grid')
        udat, vdat, xv, yv = gi.basemap.transform_vector(u,v,lons.data[0],np.flipud(lats.data).T[0],nxv,nyv,returnxy=True)
        speeddat, xspd, yspd = gi.basemap.transform_scalar(speed,lons.data[0],np.flipud(lats.data).T[0],nxv,nyv,returnxy=True)
        presdat, xpres, ypres = gi.basemap.transform_scalar(pres,lons.data[0],np.flipud(lats.data).T[0],nxv,nyv,returnxy=True)
        cmap = 'tropix_no_white'
        # Can't pass masked lat/lon/speed to barbs
        log.info('Plotting barbs')
        gi.basemap.barbs(xv, yv, udat, vdat, speeddat, ax=gi.axes, cmap=get_cmap(cmap))
        #log.info('Plotting contour')
        #gi.basemap.contour(xpres, ypres, presdat, ax=gi.axes, interpolation='nearest')
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
