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

# Python Standard libraries
import sys
import os
import socket
import argparse
import commands
import time
import logging
import random
import operator
from datetime import datetime,timedelta

#for remote debugging in wingware
try:
    import wingdbstub
except:
    print('Could not find wingdbstub from downloader.py.  I hope you\'re not trying to dubug remotely...')


# Installed libraries


# GeoIPS packages
import geoips.downloaders.Sites as Sites
from geoips.downloaders.downloaderrors import DownloaderTimeout, DownloaderGiveup,DownloaderFailed
import geoips.sectorfile as sectorfile
from geoips.sectorfile.SectorFileError import SectorFileError
from geoips.utils.log_setup import interactive_log_setup,root_log_setup
from geoips.utils.cmdargs import CMDArgs
from geoips.utils.decorators import TimeoutError
from geoips.pass_prediction.pass_prediction import pass_prediction, time_range_defaults
from geoips.utils.path.datafilename import DataFileName
from geoips.utils.qsub import qsub,wait_for_queue
from geoips.utils.main_setup import uncaught_exception,ArgParse


log = interactive_log_setup(logging.getLogger(__name__))

def downloader(data_type,
               host_type,
               sector_file=None,
               sectorlist=None,
               productlist=None,
               sectorfiles = None,
               templatefiles = None,
               start_datetime=None,
               end_datetime=None,
               nodownload=False,
               channels=None,
               data_outpath=None,
               product_outpath=None,
               noprocess=False,
               queue=None,
               max_total_jobs=500,
               max_connections=None,
               max_wait_seconds=90,
               max_num_geoips_jobs=39,
               **kwargs
              ):

    '''
    This is the downloader for data used by GeoIPS.

    +------------+-----------------------+-------------------------------------------------------+
    | Parameter: | Type:                 | Description:                                          |
    +============+=======================+=======================================================+
    | data_type  | *str*                 | Type of data to be downloaded (likely a sensor name). |
    +------------+-----------------------+-------------------------------------------------------+
    | host_type  | *str*                 | Name of the host to download data from.               |
    +------------+-----------------------+-------------------------------------------------------+

    +-------------------------+-------------------------+------------------------------------------------------------+
    | Keyword:                | Type:                   | Description:                                               |
    +=========================+=========================+============================================================+
    | sector_file             | :ref:`SectorFile`       | A :ref:`SectorFile` object containing one or more sectors. |
    |                         |                         |                                                            |
    |                         |                         | **Default:** None                                          |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | sectorlist              | :docnote:`Undocumented` | :docnote:`Undocumented`                                    |
    |                         |                         |                                                            |
    |                         |                         | **Default:** None                                          |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | productlist             | :docnote:`Undocumented` | :docnote:`Undocumented`                                    |
    |                         |                         |                                                            |
    |                         |                         | **Default:** None                                          |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | sectorfiles             | :docnote:`Undocumented` | :docnote:`Undocumented`                                    |
    |                         |                         |                                                            |
    |                         |                         | **Default:** None                                          |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | templatefiles           | :docnote:`Undocumented` | :docnote:`Undocumented`                                    |
    |                         |                         |                                                            |
    |                         |                         | **Default:** None                                          |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | start_datetime          | :docnote:`Undocumented` | :docnote:`Undocumented`                                    |
    |                         |                         |                                                            |
    |                         |                         | **Default:** None                                          |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | end_datetime            | :docnote:`Undocumented` | :docnote:`Undocumented`                                    |
    |                         |                         |                                                            |
    |                         |                         | **Default:** None                                          |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | nodownload              | :docnote:`Undocumented` | :docnote:`Undocumented`                                    |
    |                         |                         |                                                            |
    |                         |                         | **Default:** False                                         |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | channels                | :docnote:`Undocumented` | :docnote:`Undocumented`                                    |
    |                         |                         |                                                            |
    |                         |                         | **Default:** None                                          |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | data_outpath            | :docnote:`Undocumented` | :docnote:`Undocumented`                                    |
    |                         |                         |                                                            |
    |                         |                         | **Default:** None                                          |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | product_outpath         | :docnote:`Undocumented` | :docnote:`Undocumented`                                    |
    |                         |                         |                                                            |
    |                         |                         | **Default:** None                                          |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | noprocess               | :docnote:`Undocumented` | Download data but DO NOT kick off processing               |
    |                         |                         |                                                            |
    |                         |                         | **Default:** False                                         |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | queue                   | :docnote:`Undocumented` | :docnote:`Undocumented`                                    |
    |                         |                         |                                                            |
    |                         |                         | **Default:** None                                          |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | max_total_jobs          | :docnote:`Undocumented` | Maximum total number of jobs allowed before proceeding with|
    |                         |                         | download.  This includes all queued and running jobs in    |
    |                         |                         | current active queue                                       |
    |                         |                         |                                                            |
    |                         |                         | **Default:** 1500                                          |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | max_connections         | :docnote:`Undocumented` | Maximum number of connections allowed to current host      |
    |                         |                         |                                                            |
    |                         |                         | **Default:** None                                          |
    +-------------------------+-------------------------+------------------------------------------------------------+
    | max_wait_seconds        | integer                 | Longest amount of time to wait for queue                   |
    |                         |                         |                                                            |
    |                         |                         | **Default:** 90                                           |
    +-------------------------+-------------------------+------------------------------------------------------------+


    Parameters

    data_type    Key word describing the type of data to be downloaded (often sensor name)
    host_type    Key word describing the host we are getting the data from.

    sector_file When called via command line, the __main__ function sets up the
                sector_file object using sectorfile.open

    '''

    log.interactive('Running git version of downloader: max_total_jobs: '+str(max_total_jobs)+
                    ' max_connections on "'+host_type+'": '+str(max_connections)+
                    ' max_num_geoips_jobs of "'+data_type+'": '+str(max_num_geoips_jobs)+
                    ' max_wait_seconds: '+str(max_wait_seconds))

    #Open the host_type/data_type site
    site = open_site(host_type,
                     data_type,
                     start_datetime,
                     end_datetime,
                     sector_file,
                     sectorlist,
                     productlist,
                     queue
                    )
    if not max_connections:
        max_connections = site.max_connections

    #Build date and time stamps
    dt_start_of_script = datetime.utcnow()
    timestamp = dt_start_of_script.strftime('%Y%m%d.%H%M')
    hourstamp = dt_start_of_script.strftime('%Y%m%d.%H')

    #Print out startup information
    log.interactive('data_type: '  + data_type +
             ' host_type: ' + host_type +
             ' start_dt: '  + str(start_datetime) +
             ' end_dt: '    + str(end_datetime) +
             ''
             #' sectorfiles: '+ str(sectorfiles)
            )
    log.info('Hostname: ' + socket.gethostname())
    log.info('Current date time '+timestamp)
    if (nodownload):
        log.info('Not ftping files...')
    else:
        log.info('Going to ftp files...')
    log.info('\n\n')

    # Top level downloaders are GD<host_type>_<data_type>, 
    # GeoIPS processing is GW<data_type>_<host_type>
    # We only check running jobs for downloaders, because they can get in a state where they 
    # block eachother (a bunch all sitting there queued, and none ever run)
    # maury and fnmoc limit qsubnames to 0:14 (in utils/path/datafilename).
    # Probably should put this in utils/qsub.py (so datafilename and qsub and downloader call to set qsubname)
    gd_qsubname = 'GD'+host_type
    gd_qsubname = gd_qsubname[0:14]
    gw_qsubname = 'GW'+data_type
    gw_qsubname = gw_qsubname[0:14] 
    job_limits_Ronly = {gd_qsubname:max_connections}
    job_limits_RandQ = {gw_qsubname:max_num_geoips_jobs}

    if noprocess is not True:
        queue_ready = wait_for_queue(sleeptime=30,
                                 queue=queue,
                                 job_limits_Ronly=job_limits_Ronly,
                                 job_limits_RandQ=job_limits_RandQ,
                                 give_up_time=max_wait_seconds,
                                 max_total_jobs=max_total_jobs,
                                )

        if queue_ready == False:
            raise DownloaderGiveup('Queue is not ready, giving up')
    try:
        # Found in Sites/[host_type]_[data_type].py. 
        # getfilelist uses getsinglefilelist, which can be found 
        #in FTPSite.py and HTTPSite.py 
        log.info('Getting file list...')
        files = site.getfilelist(start_datetime, end_datetime)
        geoips_args = None
        geoips_args = CMDArgs()
        geoips_args.addopt('queue', queue)
        if hasattr(site, 'geoips_args'):
            for arg, argval in site.geoips_args.items():
                if argval == True:
                    log.info('Adding %s, set to True' % (arg))
                    geoips_args.addopt(arg)
                elif argval == False:
                    log.info('Not adding %s, set to False' % (arg))
                elif arg == 'productlist':
                    geoips_args.addopt('productlist',' '.join(argval))
                elif arg == 'sectorlist':
                    geoips_args.addopt('sectorlist',' '.join(argval))
                elif arg == 'productfiles':
                    geoips_args.addopt('productfiles',' '.join(argval))
                elif arg == 'sectorfiles':
                    geoips_args.addopt('sectorfiles',' '.join(argval))
                else:
                    log.info('Adding %s = %s' % (arg, argval))
                    geoips_args.addopt(arg,argval)
                    
        #site.get(files, datadir[data_type])
        if productlist:
            if geoips_args.hasopt('productlist'):
                geoips_args.delopt('productlist')
            geoips_args.addopt('productlist',' '.join(productlist))
        if sectorlist:
            if geoips_args.hasopt('sectorlist'):
                geoips_args.delopt('sectorlist')
            geoips_args.addopt('sectorlist',' '.join(sectorlist))
        if sectorfiles:
            log.info('adding sectorfiles option: '+str(sectorfiles))
            if geoips_args.hasopt('secctorfiles'):
                geoips_args.delopt('sectorfiles')
            geoips_args.addopt('sectorfiles',' '.join(sectorfiles))
        if site.sector_file.alldynamic:
            log.info('adding alldynamic option True')
            if geoips_args.hasopt('alldynamic'):
                geoips_args.delopt('alldynamic')
            geoips_args.addopt('alldynamic')
        if site.sector_file.allexistingdynamic:
            log.info('adding allexistingdynamic option True')
            if geoips_args.hasopt('alldynamic'):
                geoips_args.delopt('alldynamic')
            geoips_args.addopt('alldynamic')
        if site.sector_file.allnewdynamic:
            log.info('adding allnewdynamic option True')
            if geoips_args.hasopt('alldynamic'):
                geoips_args.delopt('alldynamic')
            geoips_args.addopt('alldynamic')
        if site.sector_file.allstatic:
            log.info('adding allstatic option True')
            if geoips_args.hasopt('allstatic'):
                geoips_args.delopt('allstatic')
            geoips_args.addopt('allstatic')

        total_num_files = None
        # If we're just checking if we have all the files, we don't
        # have to connect - this way we don't need to reserve a 
        # connection for the wrappers...
        log.info('      *** download from '+site.host)
        site.con = site.login(timeout=20)
        for ff in files:
            log.info(ff)
        log.info('Sorting '+str(len(files))+' files...')
        numfiles = 0
        dt_start_of_download = datetime.utcnow()
        lastfiledt = datetime.utcnow()
        for file in site.sort_files(files):
            log.info('')
            currdt = datetime.utcnow()
            timerunning = currdt - dt_start_of_download
            log.info('Running for '+str(timerunning)+' so far, '+str(numfiles)+' total files, time since last file: '+str(currdt-lastfiledt))
            if currdt - lastfiledt > timedelta(minutes=5):
                raise DownloaderGiveup('Last file was downloaded more than 5 minutes ago, ending download.') 
            #log.info(file)
            retval = site.get([file],just_check_if_all_downloaded=True,connect=False)
            #log.info(retval)
            if retval != False:
                log.interactive('        *** SKIPPING '+str(file)+' already downloaded')
                continue
            if (numfiles % 20 ) == 0 and noprocess is not True:
                queue_ready = wait_for_queue(sleeptime=30,
                                 queue=queue,
                                 job_limits_Ronly=job_limits_Ronly,
                                 job_limits_RandQ=job_limits_RandQ,
                                 give_up_time=max_wait_seconds,
                                 max_total_jobs=max_total_jobs,
                                )

                if queue_ready == False:
                    raise DownloaderGiveup('Already %s %s jobs in queue, or 1500 jobs total, try again next time' %
                               (max_connections, host_type)
                              )
            numfiles += 1
            site.get([file], geoips_args,connect=False,noprocess=noprocess)
            lastfiledt = datetime.utcnow()
        site.quit_connection()
    except (socket.timeout,TimeoutError),resp:
        site.quit_connection()
        raise DownloaderTimeout(str(resp)+' Failed getting list of files, try again next time')
    except (DownloaderGiveup),resp:
        site.quit_connection()
        raise DownloaderGiveup(str(resp))
    return


def open_site(host_type, data_type, start_datetime, end_datetime,
              sector_file, sectorlist, productlist, queue=None):
    #Open the site
    log.info('Opening %s %s' % (host_type, data_type))
    site = None
    # Loop through all the modules (files) in Sites
    for modulename in dir(Sites):
        # If we've already defined site, we're done.
        if site:
            continue
        module = getattr(Sites,modulename)
        # Now loop through all the actual sites found in module (file)
        for sitename in dir(module):
            currsite = getattr(module,sitename)
            # Only consider classes that have data_type and host_type defined.
            if not hasattr(currsite,'data_type') or not hasattr(currsite,'host_type'):
                continue
            # If we match the passed data_type and host_type, open the Site.
            if host_type == currsite.host_type and data_type == currsite.data_type:
                site = currsite(downloadactive=True,bandlist=None)

    if not site:
        raise DownloaderFailed('No matching '+data_type+' '+host_type+' pair, failing')

    #If the site is an ftp site, then login
    log.info(site.__class__)
    if issubclass(site.__class__, Sites.FTPSite.FTPSite):
        log.info('Logging into FTPSite')
        site.login(timeout=20)
        log.info('    Done logging in')
    site.sector_file = sector_file
    site.sectorlist = sectorlist
    site.productlist = productlist
    site.queue = queue
    return site

def print_hostpairs():
    sites = open_sites()
    sites.sort(cmp,lambda x:x.data_type)
    return '\n'.join(['  HOSTPAIR   %10s %-18s max %-2s connections to  %-55s'%(site.data_type,site.host_type,str(site.max_connections),str(site.host)) for site in sites])

def open_sites():
    sites = []
    # Loop through all the modules (files) in Sites
    for modulename in dir(Sites):
        module = getattr(Sites,modulename)
        # Now loop through all the actual sites found in module (file)
        for sitename in dir(module):
            currsite = getattr(module,sitename)
            # Only consider classes that have data_type and host_type defined.
            if hasattr(currsite,'data_type') and hasattr(currsite,'host_type'):
                sites += [currsite(downloadactive=True,bandlist=None)]
    return sites

def _get_argument_parser():
    '''Create an argument parser with all of the correct arguments.'''
    parser = ArgParse(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('data_type',nargs='?',default=None,
            help='Uses the following data_type / host_type pairs:\n'+print_hostpairs()
                       )
    parser.add_argument('host_type',nargs='?',default=None,
                        help='See data_type / host_type combinations under data_type help.\n\n'
                       )
    parser.add_arguments(['noprocess',
            'nodownload',
            'channels',
            'sectorfiles',
            'templatefiles',
            'sectorlist',
            'productlist',
            'all',
            'allstatic',
            'alldynamic',
            'tc',
            'volcano',
            'data_outpath',
            'product_outpath',
            'start_datetime',
            'end_datetime',
            'num_hours_back_to_start',
            'num_hours_to_check',
            'loglevel',
            'queue',
            'max_total_jobs',
            'max_wait_seconds',
            ])

    parser.add_argument('--max_connections', default=None,
            help='Specify the maximum number of download jobs that can be in the queue for the current host. Defaults to:\n'+\
                    '\n'.join(['    '+site.host_type+' '+str(site.max_connections) for site in open_sites()])+'\n\n')
    parser.add_argument('--list', action='store_true',help='Only open and list possible sites:\n')

    return parser

if __name__ == '__main__':
    # Set all these to None for uncaught exception handling
    emailsubject = "downloader"
    email_hndlr = None
    root_logger = None
    combined_sf = None
    args = {'data_type': None,'host_type': None,'sectorfiles':[],'productlist':None,'sectorlist':None}

    try:
        parser = _get_argument_parser()
        args = vars(parser.parse_args())

        #Set up the logger
        emailsubject = 'downloader %s %s %s %s' % (args['data_type'],
                                                  args['host_type'],
                                                  str(args['start_datetime']),
                                                  str(args['end_datetime'])
                                                 )
        root_logger,file_hndlr,email_hndlr = root_log_setup(loglevel=args['loglevel'],subject=emailsubject)
        args=parser.cleanup_args(args)
        if args['list'] == True or not args['data_type'] or not args['host_type']:
            log.info('Available sites:\n'+print_hostpairs())
            sys.exit()

        # MLS 20160108 Make sure start time is 9h prior, so we get appropriate sectorfiles.
        [args['start_datetime'], args['end_datetime']] = time_range_defaults(args['start_datetime'],
                                                                             args['end_datetime'],
                                                                             args['num_hours_back_to_start'],
                                                                             args['num_hours_to_check'],
                                                                            )
        if args['queue'] and args['queue'].lower() == 'none':
            args['queue'] = None

        #Should fix this so that either we use dynamic_templates here
        #   or sectorfile.open() uses 'templatefiles'.
        #I prefer the second solution.
        args['start_datetime'] = args['start_datetime'] - timedelta(hours=9)
        combined_sf = sectorfile.open(dynamic_templates=args['templatefiles'], 
                                **args
                                )
        # Don't want the 9h prior for downloading, just for getting dynamic sectorfiles.
        args['start_datetime'] = args['start_datetime'] + timedelta(hours=9)

        bigindent = '\n'+' '*60

        try:
            log.info('')
            combined_sf.check_sectorfile()
            log.info('')
        except SectorFileError:
            raise


        #downloader(args['data_type'], args['host_type'], sector_file=combined_sf, **args)
        try:
            downloader(sector_file=combined_sf, **args)
        except DownloaderTimeout,resp:
            log.error('Timed out on download: '+str(resp))
        except DownloaderGiveup,resp:
            log.warning('Gave up trying to kick off downloaders: '+str(resp))
        except DownloaderFailed,resp:
            log.error('Downloader failed: '+str(resp))

    # except Exception shouldn't catch KeyboardInterrupt and SystemExit
    except Exception:
        uncaught_exception(root_logger,
                    email_hndlr,
                    subject='uncaught '+str(emailsubject),
                    file=str(args['data_type'])+'_'+str(args['host_type']),
                    sectorfiles=str(args['sectorfiles']),
                    productlist=str(args['productlist']),
                    sectorlist=str(args['sectorlist']),
                    combined_sf=str(combined_sf),
                    )

