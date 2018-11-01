#!/bin/env python

# Installed Libraries
import logging

# GeoIPS Libraries

log = logging.getLogger(__name__)


def fields_plot(gi, imgkey=None):

    if not imgkey:
        return

    #log.info('Setting up fig and ax for dataset: %s with bgname: %s'%(prodname, bgname))
    #set_winds_plotting_params(gi, speeddata, platform=ds.platform_name, source=ds.source_name,
    #            prodname=prodname, bgname=bgname,
    #            start_dt=ds.start_datetime, end_dt=ds.end_datetime)

    #log.info('Plotting imgkey: %s dataset: %s'%(imgkey,ds.name))

    #cmap = None
    #if fg is not None:
    #    log.info('Plotting layer %s, %0.2f coverage'%(fg.name, 1.0*np.ma.count(fg) / fg.size ))
    #    colormapper = cm.ScalarMappable(
    #                norm=gi.colorbars[0].norm,
    #                cmap=gi.colorbars[0].cmap)
    #    currimg = colormapper.to_rgba(fg)
    #    gi.basemap.imshow(currimg,
    #                ax=gi.axes, 
    #                norm=gi.colorbars[0].norm,
    #                interpolation='nearest')
    #
    #if bg is not None:
    #    log.info('Plotting layer %s, %0.2f coverage'%(bg.name, 1.0*np.ma.count(bg) / bg.size))
    #    bgcmap = 'Greys'
    #    cfg = motion_config(bg.source_name)
    #    if bg.dataprovider in cfg.keys() \
    #        and 'plot_params' in cfg[bg.dataprovider].keys() \
    #        and bgparams in cfg[bg.dataprovider]['plot_params'].keys() \
    #        and 'cmap' in cfg[bg.dataprovider]['plot_params'][bgparams].keys():
    #        bgcmap = cfg[bg.dataprovider]['plot_params'][bgparams]['cmap']
    #    colormapper = cm.ScalarMappable(norm=colors.NoNorm(), cmap=get_cmap(bgcmap))
    #    currimg = colormapper.to_rgba(normalize(bg))
    #    gi.basemap.imshow(currimg,ax=gi.axes, interpolation='nearest')

    #if speedthin is not None:

    #    log.info('Plotting %0.2f barbs, %0.2f coverage'%(speedthin.size, 1.0*np.ma.count(speedthin) / speedthin.size))

    #    gi.basemap.barbs(lonsthin.data,latsthin.data,uthin,vthin,speedthin,ax=gi.axes,
    #                    cmap=gi.colorbars[0].cmap,
    #                    sizes=dict(height=0.8, spacing=0.3),
    #                    norm=gi.colorbars[0].norm,
    #                    linewidth=2,
    #                    length=5,
    #                    latlon=True,
    #                    )

    if gi.is_final:
        gi.finalize()


