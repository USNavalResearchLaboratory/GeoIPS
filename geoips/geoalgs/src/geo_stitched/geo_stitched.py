#!/bin/env python
import os
import logging
import numpy as np
from datetime import timedelta, datetime
from geoips.scifile.scifile import SciFile

log = logging.getLogger(__name__)

def merge_data(sectdatas,sectlons,sectlats,cfg,resolution):
    outdata = np.ma.masked_all(sectlons.shape)
    for sectdata in sectdatas.values():
        currdata = sectdata.variables[cfg['compare_channels'][sectdata.source_name]]    
        from .EnhancedImage import EnhancedImage

        enhimg = EnhancedImage(
                currdata,
                currdata.shape,
                sectlats,
                sectlons,
                )
        log.info('Enhancing imagery %s %s %s %s' % (currdata.name, currdata.platform_name, currdata.source_name, currdata.start_datetime))
        enhimg.enhanceImage(cfg)
        currdata = enhimg.Data

        log.info(' Added %s %s %s data, %0.2f coverage, total coverage now %0.2f'%
                    (sectdata.source_name, sectdata.platform_name, 
                    sectdata.start_datetime,  
                    np.ma.count(currdata)*1.0 / currdata.size, 
                    np.ma.count(outdata)*1.0 / outdata.size))
        outdata = np.ma.where(currdata.data!=currdata.fill_value, currdata, outdata)
    return outdata

def run_algorithm(datafile, sector, product, alg_config):

    sectlons,sectlats = sector.area_definition.get_lonlats()

    #####MLS Different
    sourcename = datafile.source_name
    cfg = alg_config(sourcename)
    from geoips.scifile.utils import find_datafiles_in_range
    from geoips.scifile.containers import Variable, DataSet

    variables = []
    finaldata = {}
    sectdata1s = {}

    resolution = min(sector.area_info.proj4_pixel_height, sector.area_info.proj4_pixel_width)

    # Find previous datafiles within range.
    # THIS SHOULD BE REPLACED BY A DATABASE!
    sectdatas = {}
    source_name = datafile.source_name
    platform_name = datafile.platform_name
    secttag = '%s_%s'%(source_name, platform_name)
    sectdatas[secttag] = datafile
    prev_files = []
    for prodname in cfg.keys():
        for platform, source in zip(cfg[prodname]['compare_platforms'],cfg[prodname]['compare_sources']):
            prev_files += find_datafiles_in_range(sector,
                    platform,
                    source,
                    datafile.start_datetime - timedelta(minutes=cfg[prodname]['max_time_diff']),
                    datafile.start_datetime + timedelta(minutes=cfg[prodname]['max_time_diff']),
                    )
    for prev_file in prev_files:
        sectdata = SciFile()
        sectdata.import_data([prev_file])
        source_name = sectdata.source_name
        platform_name = sectdata.platform_name
        secttag = '%s_%s'%(source_name, platform_name)
        if secttag not in sectdatas.keys():
            sectdatas[secttag] = SciFile()
            sectdatas[secttag].import_data([prev_file])

    outdata = {}
    for prodname in cfg.keys():
        outdata[prodname] = merge_data(sectdatas, sectlons, sectlats, cfg[prodname], resolution)

    return outdata, None

def geo_stitched(datafile, sector, product, workdir):
    '''
    This is an algorithm for running both heights calculations
    and motion calculations, to create a resulting text file.
    These can be run separately in order to produce full 
    output, this produces exclusively text output
    (for operational processing, running motion or heights
    separately is for development / analysis purposes)

    Any common code between heights and motion will
    be tied to the geo_stitched algorithm

    NOTE: motion_config and heights_config must define
        the same channel and same source for processing
    '''

    from .geo_stitched_config import geo_stitched_config

    # Calculate the heights
    finaldata, none = run_algorithm(datafile, sector, product, geo_stitched_config)

    return finaldata, None
            
