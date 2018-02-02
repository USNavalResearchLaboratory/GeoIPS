#!/bin/env python

# Author:
#    Naval Research Laboratory, Marine Meteorology Division
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the NRLMMD License included with this program.  If you did not
# receive the license, see http://www.nrlmry.navy.mil/geoips for more
# information.
#
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# included license for more details.


# Standard Python Libraries
import os
import sys
from glob import glob
from datetime import datetime,timedelta
import argparse
import logging


# Installed Libraries
from IPython import embed as shell


# GeoIPS Libraries
import geoips.sectorfile
import geoips.productfile
from geoips.pass_prediction.pass_prediction import time_range_defaults
from geoips.utils.path.datafilename import DataFileName
from geoips.utils.path.productfilename import ProductFileName
from geoips.utils.satellite_info import all_sats_for_sensor,all_available_sensors
from geoips.utils.main_setup import ArgParse
from geoips.utils.log_setup import interactive_log_setup,root_log_setup


log = interactive_log_setup(logging.getLogger(__name__))

SIZE_SYMBOLS = ('K','M','G','T','P','E','Z','Y')

PREFIX = {}
for ii,jj in enumerate(SIZE_SYMBOLS):
    PREFIX[jj] = 1 << (ii+1)*10

def convert_bytes(nn):
    for ss in reversed(SIZE_SYMBOLS):
        if nn >= PREFIX[ss]:
            value = float(nn) / PREFIX[ss]
            return '%.1f%s' % (value,ss)
    return '%.1fB' %nn

def latency_products(start_datetime,end_datetime,
            sensor,satellites,
            data_providers,
            overall=False,
            verbose=True,
            ):

    log.info('\n\n')
    total_hours = (end_datetime-start_datetime).days * 24 + (end_datetime-start_datetime).seconds // 3600
    log.info(str(total_hours)+' hours')

    sector_file = sectorfile.open(
                        allstatic=True,
                        alldynamic=True,
                        start_datetime = start_datetime,
                        end_datetime = end_datetime,
                        one_per_sector=True)
    
    allfiles = []
    for sat in satellites:
        log.info('Trying sat '+sat+' sensor: '+sensor)
        currdata_providers = data_providers
        currchannels = channels
        if not data_providers:
            currdata_providers = ['*']
        for data_provider in currdata_providers:
            sectors = sector_file.getsectors()
            totalnum = len(sectors)
            num = 0
            for sector in sectors:
                foundsome = False
                num += 1
                try:
                    productnames = sector.products[sensor]
                except KeyError:
                    # Skip if not defined
                    continue
                for productname in productnames:
                    #log.info('        Trying product '+productname+' from sector '+sector.name)
                    try:
                        product = productfile.open_product(sensor,productname)
                    except AttributeError:
                        # Skip if not defined
                        continue
                    # Check operational, not local. Probably should make this an option?
                    os.environ['GEOIPSFINAL'] = os.getenv('OpsGEOIPSFINAL')
                    #print os.getenv('GEOIPSFINAL')
                    currfiles = ProductFileName.list_range_of_files(sat,sensor,
                        start_datetime,
                        end_datetime,
                        sector,
                        product,
                        datetime_wildcards = {'%H':'*%H','%M':'*','%S':'*'},
                        data_provider=data_provider,
                        coverage='*',
                        intensity='*',
                        extra = '*',
                        ext='*',)
                    if currfiles:
                        foundsome=True
                    allfiles += currfiles
                if foundsome:
                    log.info('    Listing all products from sector '+sector.name+', '+str(num)+' of '+str(totalnum)+', found '+str(len(allfiles))+' files so far')
    if overall:
        totalsize,totalnum = calc_latency(allfiles,
                fileclass = 'ProductFileName',
                verbose=verbose,
                classkeys={'overall':   ['sensorname','dataprovider'],})
                            
    else: 
        totalsize,totalnum = calc_latency(allfiles,
                fileclass = 'ProductFileName',
                verbose=verbose,
                classkeys={'individual':['sensorname','productname','satname','sectorname','dataprovider'],
                            'overallproduct':   ['sensorname','productname','dataprovider'],
                            'overallsector':   ['sensorname','sectorname','dataprovider'],
                            'overall':   ['sensorname','dataprovider'],})
    log.interactive('Total size on disk for '+str(totalnum)+' products: '+convert_bytes(totalsize)+': sensor: '+sensor+' satellites: '+' ,'.join(satellites))
    return totalsize,totalnum


def calc_latency(allfiles,
                fileclass='DataFileName',
                classkeys={'individual':['productname','satname','sectorname','dataprovider']},
                verbose=False):
    ''' Pass a list of files'''

    nowtime=datetime.utcnow()

    totalsize = 0
    totalnum = 0
    totallatency = {}
    size = {}
    max_latency = {}
    min_latency = {}
    num = {}
    most_recent_fts = {}
    most_recent_fdtg = {}
    most_recent_diff = {}
    most_recent_latency = {}
    for key in classkeys.keys():
        totallatency[key] = {}
        size[key] = {} 
        max_latency[key] = {} 
        min_latency[key] = {} 
        num[key] = {} 
        most_recent_fts[key] = {} 
        most_recent_fdtg[key] = {} 
        most_recent_diff[key] = {}
        most_recent_latency[key] = {}
    currnum = 0
    log.info('Looping through all '+str(len(allfiles))+' files')

    for file in sorted(allfiles):
        currnum += 1
        if os.path.isdir(file):
            continue
        try:
            filesize = float(os.stat(file).st_size)
        except OSError:
            continue
        fts = datetime.utcfromtimestamp(os.stat(file).st_mtime)
        #print file
        # Use the string passed as fileclass to open the appropriate GeoIPS FileName object 
        #   (ProductFileName or DataFileName)
        #gfn = getattr(sys.modules[__name__],fileclass)(os.path.basename(file))
        gfn = getattr(sys.modules[__name__],fileclass)(file)
        if not gfn or not gfn.datetime:
            log.warning('Bad file ? SKIPPING '+file)
            continue
        latency = (fts-gfn.datetime).total_seconds() / 3600.0

        #if ((not channels or gfn.channel in channels) 
        #    and (gfn.satname == 'unknown' or gfn.satname == 'aqua' or gfn.satname == 'terra' or gfn.satname in satellites
        #        or gfn.sensorname in satellites) 
        #    and (not data_providers or gfn.dataprovider in data_providers)):
        #    if gfn.satname == 'unknown':
        #        gfn.satname = file.split('.')[-1]

        totalsize+=filesize
        totalnum += 1
        for calctype in classkeys.keys():
            currkey = ' '.join([getattr(gfn,gfnkey) if hasattr(gfn,gfnkey) else '' for gfnkey  in classkeys[calctype]])
            #print currkey
            try:
                size[calctype][currkey] += filesize
                totallatency[calctype][currkey] += latency 
                num[calctype][currkey] += 1
                if latency > max_latency[calctype][currkey]:
                    max_latency[calctype][currkey] = latency
                if latency < min_latency[calctype][currkey]:
                    min_latency[calctype][currkey] = latency
                if gfn.datetime > most_recent_fdtg[calctype][currkey]:
                    most_recent_fdtg[calctype][currkey] = gfn.datetime
                    most_recent_latency[calctype][currkey] = (fts - gfn.datetime).total_seconds() / 3600.0
                if fts > most_recent_fts[calctype][currkey]:
                    most_recent_fts[calctype][currkey] = fts
                    most_recent_diff[calctype][currkey] = (nowtime - fts).total_seconds() / 3600.0

            except KeyError:
                size[calctype][currkey] = filesize
                totallatency[calctype][currkey] = latency
                num[calctype][currkey] = 1
                max_latency[calctype][currkey] = latency
                min_latency[calctype][currkey] = latency
                most_recent_fts[calctype][currkey] = fts
                most_recent_fdtg[calctype][currkey] = gfn.datetime
                most_recent_diff[calctype][currkey] = (nowtime - fts).total_seconds() / 3600.0
                most_recent_latency[calctype][currkey] = (fts - gfn.datetime).total_seconds() / 3600.0
        if verbose:
            log.info('%d of %d: %3.2f %s %s' % (currnum,len(allfiles),latency,fts.strftime('%Y%m%d.%H%M'),file))
        if currnum% 1000 == 0:
            log.info(' On number '+str(currnum))
    log.info('\nCurrent time UTC: '+str(datetime.utcnow()))
    log.info('From '+str(start_datetime)+' to '+str(end_datetime))
    for calctype in sorted(classkeys.keys()):
        printstr = calctype.upper()+' STATS FOR '
        currkeys = totallatency[calctype].keys()
        for key in currkeys:
            log.interactive(printstr+' '+str(key))
            log.interactive('      Average latency: %3.2f  Max latency: %3.2f  Min latency: %3.2f  Total Files: %d   Most recent: system time / how long ago: %s / %3.2f  filename time / latency: %s / %3.2f' % (totallatency[calctype][key] / num[calctype][key],max_latency[calctype][key],min_latency[calctype][key],num[calctype][key],most_recent_fts[calctype][key].strftime('%Y%m%d.%H%M'),most_recent_diff[calctype][key],most_recent_fdtg[calctype][key].strftime('%Y%m%d.%H%M'),most_recent_latency[calctype][key]))
            log.interactive('      Total size on disk: '+convert_bytes(size[calctype][key]))
    return totalsize,totalnum

     
    

def latency(start_datetime,end_datetime,
            sensor,satellites,
            data_providers,
            channels,
            overall=False,
            verbose=True,
            ):

    log.info('\n\n')
    nowtime = datetime.utcnow()
    total_hours = (end_datetime-start_datetime).days * 24 + (end_datetime-start_datetime).seconds // 3600
    log.info(str(total_hours)+' hours')
    
    allfiles = []
    for sat in satellites:
        log.info('Trying sat '+sat+' sensor: '+sensor)
        currdata_providers = data_providers
        currchannels = channels
        if not data_providers:
            currdata_providers = ['*']
        if not channels:
            currchannels = ['*']
        for data_provider in currdata_providers:
            for channel in currchannels:
                allfiles += DataFileName.list_range_of_files(sat,sensor,
                    start_datetime,
                    end_datetime,
                    datetime_wildcards = {'%H':'*%H','%M':'*','%S':'*'},
                    data_provider=data_provider,
                    resolution='*',
                    channel=channel,
                    producttype='*',
                    area='*',
                    extra = '*',
                    ext='*',
                    forprocess=False)

    if overall:
        totalsize,totalnum = calc_latency(allfiles,
                fileclass = 'DataFileName',
                verbose=verbose,
                classkeys={'overall':['sensorname','satname','dataprovider'],})
    else: 
        totalsize,totalnum = calc_latency(allfiles,
                fileclass = 'DataFileName',
                verbose=verbose,
                classkeys={'individual':['sensorname','satname','channel','dataprovider'],
                            'overall':   ['sensorname','satname','dataprovider'],})
    log.interactive('Total size on disk for '+str(totalnum)+' data files: '+convert_bytes(totalsize)+': sensor: '+sensor+' satellites: '+', '.join(satellites))
    return totalsize,totalnum


def _get_argument_parser():
    '''Create an argument parser with all of the correct arguments.'''
    parser = ArgParse(formatter_class=argparse.RawTextHelpFormatter,
            description='Get latency stats for various sensors\n')
    parser.add_argument('sensor', nargs='?', default=None, help='Call with no sensor to print summary for ALL sensors\nSingle sensor name\n  '+'\n  '.join(all_available_sensors()))
    parser.add_argument('-d','--data_files', action='store_true',  help='Compute latency for data files')
    parser.add_argument('-p','--products', action='store_true',  help='Compute latency for products')
    parser.add_argument('-o','--overall', action='store_true',  help='Only output overall latency for data provider / sensor, not individual files')
    parser.add_arguments([
                        'start_datetime',
                        'end_datetime',
                        'verbose',
                        'loglevel',
                        'num_hours_back_to_start',
                        'num_hours_to_check'
                        ])
    return parser

if __name__ == '__main__':
    parser = _get_argument_parser()
    args = vars(parser.parse_args())

    #print args['loglevel']

    root_logger,file_hndlr,email_hndlr = root_log_setup(loglevel=args['loglevel'],subject='')

    [start_datetime, end_datetime] = time_range_defaults(args['start_datetime'],
                                                                         args['end_datetime'],
                                                                         args['num_hours_back_to_start'],
                                                                         args['num_hours_to_check'],
                                                                        )

    totalsize = 0
    totalnum = 0
    totalsize_products = 0
    totalnum_products = 0
    if args['products']:
        log.interactive('Requested product stats')
    if args['data_files']:
        log.interactive('Requested data stats')
    if not args['products'] and not args['data_files']:
        log.interactive('Did not request data or products, giving you data')
    log.interactive('Starting at '+str(start_datetime))
    log.interactive('Ending   at '+str(end_datetime))
    #print args['sensor']
    if not args['sensor']:
        for sensor in all_available_sensors():
            satellites = all_sats_for_sensor(sensor)
            data_providers = None
            channels = None
            #if args['sensor'] == 'modis':
            #    data_providers = ['lance']
            #    channels = ['MOD021KM','MOD02HKM','MOD02QKM','MOD03']
            #if args['sensor'] == 'viirs':
            #    data_providers = ['noaa_ops','cspp_dev','ssec_viirsrdr']
            #    channels = ['sdr','ncc']

            # Compute latency for data if nothing is specified.
            if args['data_files'] or not args['products']:
                currsize,currnum = latency(start_datetime,end_datetime,sensor,satellites,data_providers,channels,args['overall'],args['verbose'])
                totalsize += currsize
                totalnum += currnum
            if args['products']:
                currsize,currnum = latency_products(start_datetime,end_datetime,sensor,satellites,data_providers,args['overall'],args['verbose'])
                totalsize_products += currsize
                totalnum_products += currnum
            if totalsize:
                log.info('So far: Total size of all '+str(totalnum)+' data files on disk: '+convert_bytes(totalsize))
            if totalsize_products:
                log.info('So far: Total size of all '+str(totalnum_products)+' products on disk: '+convert_bytes(totalsize_products))
            log.interactive('')
    else:
        satellites = all_sats_for_sensor(args['sensor'])
        #print satellites
        data_providers = None
        channels = None
        #if args['sensor'] == 'modis':
        #    data_providers = ['lance']
        #    channels = ['MOD021KM','MOD02HKM','MOD02QKM','MOD03']
        #if args['sensor'] == 'viirs':
        #    #data_providers = ['noaa_ops','cspp_dev','ssec_viirsrdr']
        #    #channels = ['sdr','ncc']
        #    pass

        #if args['sensor'] == 'modisold':
        #    satellites = ['aqua','terra']
        if args['data_files'] or not args['products']:
            currsize,currnum = latency(start_datetime,end_datetime,args['sensor'],satellites,data_providers,channels,args['overall'],args['verbose'])
            totalsize += currsize
            totalnum += currnum
            
        if args['products']:
            currsize,currnum = latency_products(start_datetime,end_datetime,args['sensor'],satellites,data_providers,args['overall'],args['verbose'])
            totalsize_products += currsize
            totalnum_products += currnum

    log.interactive('')

    if totalsize:
        log.interactive('Total size of all '+str(totalnum)+' data files on disk: '+convert_bytes(totalsize))
    if totalsize_products:
        log.interactive('Total size of all '+str(totalnum_products)+' products on disk: '+convert_bytes(totalsize_products))
