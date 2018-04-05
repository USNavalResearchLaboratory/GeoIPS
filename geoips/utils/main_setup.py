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


# Python Standard Libraries
import smtplib
from email.mime.text import MIMEText
import traceback
from subprocess import check_output
import argparse
import os
import sys
import logging


# Installed Libraries


# GeoIPS Libraries
from .log_setup import interactive_log_setup,add_email_hndlr,base_email_subject,toemails,fromemail


log = interactive_log_setup(logging.getLogger(__name__))


def uncaught_exception(root_logger=None,
                        email_hndlr=None,
                        subject='Unknown Subject',
                        file=None,
                        sectorfiles=[],
                        productlist=None,
                        sectorlist=None,
                        combined_sf=None):
    if email_hndlr != None:
        root_logger.removeHandler(email_hndlr)
    if root_logger != None:
        #root_logger,email_hndlr = add_email_hndlr(root_logger,subject=subject)

        root_logger.exception('This is terrible!  Fix me please!\n'+
                        'file: '+str(file)+'\n'+
                        'sectorfiles: '+str(sectorfiles)+'\n'+
                        'sectorlist: '+str(sectorlist)+'\n'+
                        'productlist: '+str(productlist)+'\n'+
                        'combined_sf: '+str(combined_sf))
    else:
    #    msg = MIMEText(traceback.format_exc())
    #    msg['Subject'] = base_email_subject+' MAJOR UNCAUGHT EXCEPTION '+subject
    #    msg['From'] = fromemail
    #    msg['To'] = ', '.join(toemails)

    #    s = smtplib.SMTP('localhost')
    #    s.sendmail(fromemail, toemails, msg.as_string())
    #    s.quit()
        raise

def available_queues():
    queues = ['fourinone@kahuna','batch@kahuna','sat@nassat1','satq','idps']
    #queues = []
    try:
        lines = check_output(['qstat','-q']).split('\n')
        started = False
        for line in lines:
            flds = line.split()
            if flds and 'server' in flds[0]:
                hostname = flds[1].split('.')[0]
            if flds and '----' in flds[0]:
                started = True
                continue
            elif started and flds:
                queues += [flds[0],flds[0]+'@'+hostname]
            else:
                continue
        return queues
    except:
        return queues
         

class ArgParse(argparse.ArgumentParser):
    def cleanup_args(self,args):
        print('\n\n')
        print('COMMAND LINE CALL: '+' '.join(sys.argv)+'\n\n')
        #if 'queue' in self.arglist and args['queue'] not in available_queues():
        #    log.error('Queue '+str(args['queue'])+' does not exist, setting to None')
        #    args['queue'] = None
        if 'queue' in self.arglist and (not args['queue'] or args['queue'].lower() == 'none'):
            log.error('Setting queue to None')
            args['queue'] = None

        if 'channels' in self.arglist and args['channels']:
            args['channels'] = args['channels'].split()
        if 'queue' in self.arglist and args['queue']:
            log.info('queue: '+str(args['queue']))
        if 'sectorfiles' in self.arglist and args['sectorfiles']:
            args['sectorfiles'] = args['sectorfiles'].split()
            log.info('Doing static files:')
            log.info(args['sectorfiles'])
        if 'productfiles' in self.arglist and args['productfiles']:
            args['productfiles'] = args['productfiles'].split()
        if 'productlist' in self.arglist and args['productlist']:
            log.info(args['productlist'])
            args['productlist'] = args['productlist'].split()
            args['productlist'] = [x.lower() for x in args['productlist']]
        if 'sectorlist' in self.arglist and args['sectorlist']:
            log.info('Doing sectors: '+str(args['sectorlist']))
            args['sectorlist'] = args['sectorlist'].split()
            args['sectorlist'] = [x.lower() for x in args['sectorlist']]
        if 'all' in self.arglist and args['all']:
            args['allstatic'] = True
            args['alldynamic'] = True
        if 'mp_max_cpus' in self.arglist and args['mp_max_cpus']:
            log.info('mp_max_cpus: '+str(args['mp_max_cpus']))
        if 'no_multiproc' in self.arglist and args['no_multiproc']:
            log.info('no_multiproc: '+str(args['no_multiproc']))
        if 'extra_dirs' in self.arglist and args['extra_dirs']:
            args['extra_dirs'] = args['extra_dirs'].split()
        return args

    def add_arguments(self,arglist):
        self.arglist = arglist
        if 'file' in arglist: self.add_argument('file', nargs='?', default=None, type=os.path.abspath,
                        help='''Fully qualified path to data file to be processed.'''
                       )
        if 'path' in arglist: self.add_argument('path', nargs='?', default=None, type=os.path.abspath,
                        help='''Path data file or directory.'''
                       )
        if 'paths' in arglist: self.add_argument('paths', nargs='*', default=None, type=os.path.abspath,
                        help='''List of paths to multiple data files or directories.'''
                       )
        if 'satellite' in arglist: self.add_argument('satellite', help='Single satellite name')
        if 'sensor' in arglist: self.add_argument('sensor', help='Single sensor name')
        if 'sector' in arglist: self.add_argument('sector', help='Single sector name')
        if 'product' in arglist: self.add_argument('product', help='Single product name')
        if 'list' in arglist: self.add_argument('--list',action='store_true',
                            help='only list overpasses/data files and not actually kick off processing')
        if 'sector_name' in arglist: self.add_argument('--sector_name',default=None)
        if 'nofinal' in arglist: self.add_argument('--nofinal', action='store_true',
                        help='''If nofinal is included command line, do not produce final Image
                                with gridlines and coastlines (only produce GEOIPSTEMP images)''')

        if 'sectorlist' in arglist: self.add_argument('-s', '--sectorlist', nargs='?', default=None,
                        help='''A list of short sector names over which the data file should be processed.
                             Short sector names are available in the "name" attribute of the "sector"
                             elements in the sector files available in $GEOIPS/sectorfiles.
                             '''
                       )
        if 'productlist' in arglist: 
            log.info('productlist included')
            self.add_argument('-p', '--productlist', nargs='?', default=None,
                        help='''A list of the names of the products that should be produced.
                             Names are available in the "name" attribute of "product" elements
                             in the product files available in $GEOIPS/productfiles/<sensorname>
                             '''
                        )
        if 'product_outpath' in arglist: self.add_argument('--product_outpath',default=None,type=os.path.abspath),
        if 'outpath' in arglist: self.add_argument('--outpath',default='./',type=os.path.abspath),
        if 'forcereprocess' in arglist: self.add_argument('-f','--forcereprocess',action='store_true'),
        #if 'loglevel' in arglist: self.add_argument('-l','--loglevel',default=logging.INFO,type=lambda ll:getattr(logging,ll.upper()),
        #                    help='Specify log level: error, warning, info, interactive, debug.\n\n'
        #                    )
        if 'channels' in arglist: self.add_argument('--channels', nargs='?', default=None,
                            help='Only for viirs/modis, since they have separate files for '+\
                                    'the separate channels \n'+\
                                    'specify which channels to download, and then include in tdf file'+\
                                    'if we are converting after download (viirs)\n\n'
                           )
        if set(['loglevel','verbose','quiet']).intersection(set(arglist)):
            log_levels = self.add_argument_group(title='Logging levels')
            if 'loglevel' in arglist: log_levels.add_argument('-l','--loglevel',default='info')
            if 'verbose' in arglist: log_levels.add_argument('-v','--verbose',action='store_true',help='Print more output'),
            if 'quiet' in arglist: log_levels.add_argument('-q','--quiet',action='store_true',help='Suppress all output'),
        if set(['all','allstatic','alldynamic','tc','volcano']).intersection(set(arglist)):
            sect_types = self.add_argument_group(title='Sector Types')
            if 'all' in arglist: sect_types.add_argument('--all',action='store_true',
                                    help='Process all sectors, including static and dynamic.')
            if 'allstatic' in arglist: sect_types.add_argument('--allstatic',action='store_true',
                                    help='Adds $STATIC_SECTORFILEPATH to --sectorfiles\n'+\
                                    '(call with --allstatic --alldynamic to get EVERYTHING)\n\n'
                                    )
            if 'alldynamic' in arglist: sect_types.add_argument('--alldynamic',action='store_true',
                                help='Include all existing dynamic sectors \n'+\
                                '(created from past flat tc sectorfiles and past volcano files\n'+\
                                'and all new dynamic sectors \n'+\
                                '(created from current flat tc sectorfiles and current volcano files\n'+\
                                '(call with --allstatic --alldynamic to get EVERYTHING)\n\n'
                                )
            if 'tc' in arglist: sect_types.add_argument('--tc',action='store_true',
                                    help='Process tropical cyclone sectors.  Does nothing if --all and --alldynamic is set.')
            if 'volcano' in arglist: sect_types.add_argument('--volcano',action='store_true',
                                    help='Process volcano sectors.  Does nothing if --all or --alldynamic is set.')
        if set(['mp_max_cpus', 'no_multiproc','memusg']).intersection(set(arglist)):
            mp_opts = self.add_argument_group(title='Multiprocessing Options')
            if 'no_multiproc' in arglist: mp_opts.add_argument('--no_multiproc', action='store_true',
                                    default=False,
                                    help='Explicitly turn off multiprocessing regardless of all other options. \n\n'
                                )
            if 'mp_max_cpus' in arglist: mp_opts.add_argument('--mp_max_cpus', default=1,
                                    help='Specify the maximum number of cpus to use during multiprocessing. \n'+\
                                'Be sure to call qsub with the appropriate number of cpus when calling driver.py!\n\n'
                                )
            if 'printmemusg' in arglist: self.add_argument('--printmemusg', action='store_true',
                        help='''If printmemusg is included command line, keep detailed memory usage 
                                stats during processing''')
        if set(['sectorfiles','templatefiles','productfiles']).intersection(set(arglist)):
            sect_files = self.add_argument_group(title='Sector and Product Files')
            if 'sectorfiles' in arglist: sect_files.add_argument('--sectorfiles', nargs='?',default=[],
                                    help='Specify alternate sectorfiles or sectorfiles directory. \n'+\
                                'Used in sectorfile.open, overrides $STATIC_SECTORFILEPATH.\n'+\
                                'If this option is included, no dynamic sectors will be included \n'+\
                                'unless another dynamic sector option is explicitly set\n'+\
                                '(call with --allstatic --alldynamic to get EVERYTHING)\n\n'
                                )
            if 'templatefiles' in arglist: sect_files.add_argument('--templatefiles', nargs='?',default=[],
                                help='Specify alternate template files or templatefile directory. \n'+\
                                'Used in sectorfile.open, overrides $TEMPLATEPATH\n'+\
                                'If this option is included, no static sectors will be included\n'+\
                                'unless --sectorfiles or --allstatic is explicitly set\n'+\
                                '(call with --allstatic --alldynamic to get EVERYTHING)\n\n'
                                )
            # Implement this eventually. Not actually used anywhere yet.
            if 'productfiles' in arglist: sect_files.add_argument('--productfiles', nargs='?',default=None,
                                help='Specify alternate product files or productfiles directory. \n'+\
                                'Used in productfile.open, overrides INTERNAL/EXTERNAL_PRODUCTFILEPATH\n'+\
                                'If this option is included, no operational products \n'+\
                                'will be included, only products from the provided path.\n\n'
                                )

        if set(['queue','next','max_total_jobs','max_wait_seconds','max_connections']).intersection(set(arglist)):
            pbs_opts = self.add_argument_group(title='PBS Queue Options')
            if 'queue' in arglist: pbs_opts.add_argument('-q', '--queue', 
                            default=os.getenv('DEFAULT_QUEUE'), metavar='queue@hostname',
                            help='Specifies the name of the PBS queue to which spawned jobs will be passed.  '+
                                   'Defaults to DEFAULT_QUEUE.'
                             )
            if 'next' in arglist: pbs_opts.add_argument('-n', '--next', action='store_false')
            if 'max_total_jobs' in arglist: pbs_opts.add_argument('--max_total_jobs', default=1500,
                                help='Specify the maximum number of jobs that can be in the queue for downloads to run\n'+\
                                        'Default: 1500 jobs\n\n'
                               )
            if 'max_wait_seconds' in arglist: pbs_opts.add_argument('--max_wait_seconds', default=90,
                                help='Specify the maximum amount of time we will wait for the queue to clear before giving up and moving on to the next file\n'+\
                                        'Default: 90 seconds\n\n'
                               )
        if set(['extra_dirs','nodownload','nownload','noprocess','clean','forceclean']).intersection(set(arglist)):
            download_opts = self.add_argument_group(title='Download Options')
            if 'extra_dirs' in arglist: download_opts.add_argument('--extra_dirs',default=[],
                                help='Supply an alternate data file directory (ie, /sb2/viirs)')
            if 'data_outpath' in arglist: download_opts.add_argument('--data_outpath', default=None,
                        help='Only for sector-based downloads (code could be '+\
                                'easily modified to include \n'+\
                                'exhaustive downloads, just hasn\'t been modified yet). '+\
                                'Pass an alternate path besides default data dir:\n'+\
                                #'\n'.join(['    %-12s:  %s' % (key,datadir[key]) for key in datadir])+\
                                '\n\n'
                       )
            if 'nodownload' in arglist: download_opts.add_argument('--nodownload',action='store_true',
                                help='''Do not kick off downloader to fill 
                                in any missing data. The downloader will qsub jobs, even if -q is not set!''')
            if 'download' in arglist: download_opts.add_argument('--download',action='store_true',
                                help='''Force downloader to run to fill 
                                in any missing data. The downloader will qsub jobs, even if -q is not set!''')
            if 'noprocess' in arglist: download_opts.add_argument('--noprocess', action='store_true',
                        help='If included, we will NOT process the data as it comes in, only download \n'+\
                            'I think this might only work for sector-based download types... \n'+\
                            'This ultimately gets passed to the postprocs method, which then \n'+\
                            'Passes to  the converter (for viirs at least). The converter kicks\n '+\
                            'off the driver, unless this option has been included\n\n'
                       )
            if 'clean' in arglist: download_opts.add_argument('--clean',action='store_true',
                            help='Prompt for removing previously created files')
            if 'forceclean' in arglist: download_opts.add_argument('--forceclean',action='store_true',
                            help='NO Prompt for removing previously created files')
        if set(['start_datetime','end_datetime','num_hours_back_to_start','num_hours_to_check']).intersection(set(arglist)):
            timerange_opts = self.add_argument_group(title='Time Range Options for Dynamic')
            if 'start_datetime' in arglist: timerange_opts.add_argument('-S','--start_datetime', default=None,
                                help='Only download data that falls after this time.\n\n'
                               )
            if 'end_datetime' in arglist: timerange_opts.add_argument('-E','--end_datetime', default=None,
                                help='Only download data that falls before this time.\n\n'
                               )
            if 'num_hours_back_to_start' in arglist: timerange_opts.add_argument('-B','--num_hours_back_to_start', default=None,
                                help='Start downloading data num_hours_back_to_start hours ago. \n'+\
                                        '*trumps -S and -E: if either -B or -N are included, \n'+\
                                        '-S and -E are ignored.\n\n'
                               )
            if 'num_hours_to_check' in arglist: timerange_opts.add_argument('-N','--num_hours_to_check', default=None,
                                help='Download num_hours_to_check hours worth of data.\n'+\
                                        '*trumps -S and -E: if either -B or -N are included, \n'+\
                                        '-S and -E are ignored.\n\n'
                               )
