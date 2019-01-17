#!/usr/bin/env python

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
import argparse
import os
import commands
import re
import sys
from glob import glob
import logging 
from datetime import datetime,timedelta
import operator
import time

# Installed Libraries
from IPython import embed as shell

# GeoIPS Libraries
import geoips.productfile as productfile
import geoips.sectorfile as sectorfile
from geoips.utils.log_setup import interactive_log_setup,root_log_setup
from geoips.utils.cmdargs import CMDArgs
from geoips.scifile import SciFile
from geoips.sectorfile.SectorFileError import SectorFileError
from geoips.pass_prediction.pass_prediction import pass_prediction
from geoips.utils.path.datafilename import DataFileName
from geoips.utils.path.productfilename import ProductFileName
from geoips.utils.satellite_info import SatSensorInfo
from geoips.utils.qsub import qsub, wait_for_queue
from geoips.utils.main_setup import uncaught_exception,ArgParse
from geoips.utils.plugin_paths import paths as gpaths

bigindent='\n'+' '*20
log = interactive_log_setup(logging.getLogger(__name__))

default_data_type = {
        'modis':'modislads',
        #'viirs':'viirsrdr',
        'viirs':'viirs',
        'rscat':'rscat',
        }

# if we are trying to rerun something and need to download
# data, where do we get it from?
default_host_type = {
        'viirs':'sips',
        'viirsrdr':'ssec',
        'modis':'lance',
        'modislads':'ladsweb',
        'rscat':'jplrscat'
        }

run_old_pp = False

class ProductError(Exception):
    def __init__(self,msg):
        self.value = msg
    def __str__(self):
        return self.value 

def find_existing_products(sensor,sector_file,sectorlist,productlist,datestrlist,clean,forceclean):
    ''' This should use utils.path.productfilename to find a list of files that match given 
        sensor/sectors/products, in order to delete them if needed (sometimes if you 
        change sector shapes or sizes, change product parameters, etc, you don't want to 
        merge your old granules in !). 
        Currently not implemented though, never updated to work 
        from utils.path rather than genplot.filename. '''
    if not clean and not forceclean:
        log.info('Did not request clean - not checking existing products')
        return []
    # Opens ALL products in utils.plugin_paths.PRODUCTFILEPATHS 
    pf = productfile.open()
    files = []
    paths = []
    if not sectorlist:
        sectorlist = sector_file.sectornames() 
    for sectorname in sectorlist:
        log.info('  Checking for existing files for '+sectorname)
        sect = sector_file.open_sector(sectorname)
        if sect is None:
            log.info('    Skipping sector '+sectorname)
            continue
        ni = sect.name_info
        #mi = sect.master_info
        if not productlist:
            try:
                productlist = sect.products[sensor]
            except KeyError:
                log.info('    No products for sensor '+sensor)
                productlist = []
        for productname in productlist:
            prod = pf.open_product(productname)
            if prod == None:
                raise ProductError('!!!!!!! Product '+productname+' does not exist !!!!!!!!!!!!')
            #tcpath = LegacyTCIRVisProductPath(ni.region,ni.subregion,prod.name,sensor,str(mi.pixel_width)+'km')
            #satmetocpath = LegacyNexsatProductPath(ni.region,ni.subregion,prod.name,sensor,basepath=os.getenv('PRIVATE'),fullpath=None,resolution=mi.pixel_width)
            #nexsatpath = LegacyNexsatProductPath(ni.region,ni.subregion,prod.name,sensor,basepath=os.getenv('PUBLIC'),fullpath=None,resolution=mi.pixel_width)
            #temppath = ProductPath(ni.region,ni.subregion,prod.name,sensor,basepath=gpaths['GEOIPSTEMP'])
            #finalpath = ProductPath(ni.region,ni.subregion,prod.name,sensor)
            #for datestr in datestrlist:
            #    files.extend(glob(temppath.dirname+'/'+datestr+'*'))
            #    files.extend(glob(finalpath.dirname+'/'+datestr+'*'))
            #    files.extend(glob(tcpath.dirname+'/'+datestr+'*'))
            #    files.extend(glob(nexsatpath.dirname+'/'+datestr+'*'))
            #    files.extend(glob(satmetocpath.dirname+'/'+datestr+'*'))
            #paths.extend([temppath.dirname,finalpath.dirname,tcpath.dirname,nexsatpath.dirname])


    if files:
        lsfiles= []
        for file in files:
            lsfiles.append(commands.getoutput('ls -l '+file))
        loglist = []
        if forceclean == False and clean == False:
            loglist.append('Found the following product images, not deleting any:')
        
        if forceclean == True:
            loglist.append('Going to delete existing files without prompting')
            clean = True
        elif clean == True:
            loglist.append('Going to delete existing files with prompting')
            wronganswer = 1
            while wronganswer:
                val = raw_input('  Remove all files from specified date(s) in:'+'\n    '.join(paths)
                        +'\n '+'\n '.join(lsfiles)+'\nEnter yes or no: ')
                if val == 'yes':
                    loglist.append('  Ok, going to delete files')
                    wronganswer = 0
                elif val == 'no':
                    loglist.append('  Ok, not going to delete files')
                    clean = False
                    wronganswer = 0
                else:
                    loglist.append('  Please enter yes or no')
        for file in files:
            if '/users/'+os.getenv('USER')+'/branch' not in file and not os.getenv('GEOIPS_OPERATIONAL_USER'):
                loglist.append('NOT DELETING FILE, NOT IN YOUR BRANCH! '+file)
            elif clean == True or forceclean == True:
                loglist.append('DELETED FILE: '+file)
                try:
                    os.unlink(file)
                except OSError:
                    loglist.append('FILE ALREADY DELETED: '+file)
            else:
                loglist.append(file)
        log.info('\n    '.join(loglist))
        return loglist
    else:
        log.info('NO PRODUCT IMAGES FOUND')
        log.debug('IN\n                                '+
                        '\n                                '.join(paths)+'\n')
        return []

def find_available_data_files(opasses,start_dt,satellite,sensor,extra_dirs,prodtype=None,ext='*'):
    all_files = []
#    runfulldir = None
    overall_start_dt = start_dt
    overall_end_dt = start_dt
    #print opasses
    for opass in sorted(opasses,key=operator.attrgetter('basedt')):

        log.interactive('Trying opass: '+str(opass))


        dfn = DataFileName.from_satsensor(satellite,sensor,wildcards=True)
#        dfn.ext = ext
        if not prodtype:
            #prodtype = '*'
            prodtype = dfn.sensorinfo.FName['default_producttype']
        #print prodtype
#        dfn.producttype = prodtype

#        runfulldir = dfn.sensorinfo.FName['runfulldir']

        # If this is a long overpass, make sure we get the data files
        # coming before the overpass time
        mins_per_file = dfn.sensorinfo.mins_per_file
        startdt = opass.startdt - timedelta(minutes=mins_per_file)
        enddt = opass.enddt + timedelta(minutes=mins_per_file)
        if startdt < overall_start_dt:
            overall_start_dt = startdt
        overall_end_dt = enddt

        all_files += DataFileName.list_range_of_files(satellite,sensor,
                    startdt,
                    enddt,
                    datetime_wildcards = {'%H':'%H','%M':'*','%S':'*'},
                    data_provider='*',
                    resolution='*',
                    channel='*',
                    producttype=prodtype,
                    area='*',
                    extra = '*',
                    ext='*',
                    forprocess=True,
                    )
        all_files = list(set(all_files))
        log.interactive('        Total files so far: '+str(len(all_files)))

    if all_files:
        log.interactive('Available files:'+bigindent+bigindent.join(commands.getoutput('ls --full-time -d '+str(file)) for file in sorted(all_files))+'\n\n')
    return all_files

#def remove_duplicate_files(fnames,overall_start_dt,overall_end_dt):
#    '''Removes duplicate files from a list of files of the same type.
#    Duplicates are defined as files that contain the same data,
#    but are simply from different data sources.
#    For example, VIIRS data is downloaded from both CIMMS and FNMOC
#    each of which receive a different file name.'''
#    best_fnames = []
#    if len(fnames) == 0:
#        return best_fnames
#    file_names = {}
#    #Loop over the filenames and put in a dictionary whose keys are
#    #   objects of the type defined by dt_class and whose keys are
#    #   lists of file names
#    # Only use string of Ymd.HM because often the different data 
#    #   sources have varying seconds for granule times
#    for fname in fnames:
#        log.interactive(fname)
#        if os.path.isdir(fname):
#            files = glob(fname+'/*')
#            # Skip empty directories...
#            if files:
#                firstfile = glob(fname+'/*')[0]
#            else:
#                continue
#            dfn = DataFileName(firstfile)
#        else:
#            dfn = DataFileName(fname)
#        # Sometimes our date/time wildcards return extra files - skip those.
#        if dfn.datetime < overall_start_dt or dfn.datetime > overall_end_dt:
#            continue
#        # MLS add everything but dataprovider and extra to key
#        dfn.dataprovider = 'x'
#        dfn.extra = 'x'
#        dfn.channel = 'x'
#        if os.path.isdir(fname):
#            tag = dfn.dirname().name
#        else:
#            tag = dfn.name
#        #log.interactive(tag+' '+fname)
#        #dtstr = dt
#        if not file_names.has_key(tag):
#            file_names[tag] = []
#        file_names[tag].append(fname)
#    #Loop over the keys of file_dts and gather a list of filenames
#    #   with only one per date and time.  Removes files of "lower prescidence"
#    #   as defined by get_precedence()
#    for fnstr in file_names.keys():
#        log.info('checking fname for precedence: '+str(fnstr))
#        best_fnames.append(sorted(file_names[fnstr], key=get_precedence)[0])
#        #shell()
#    return best_fnames

#def get_precedence(fnames):
#    precedence = []
#    search = [re.compile('.*-pid.*'),
#              re.compile('.*x-x')]
#    #search = [re.compile('[0-9]{8}\.[0-9]{6}\.viirs\.npp\.afwa_ops\.([^.]*\.)\.*tdf'),
#    #          re.compile('[0-9]{8}\.[0-9]{6}\.viirs\.npp\.noaa_ops\.([^.]*\.)\.*tdf'),
#    #          re.compile('[0-9]{8}\.[0-9]{6}\.viirs\.npp\.cspp_dev\.([^.]*\.)\.*tdf'),
#    #          re.compile('[0-9]{8}\.[0-9]{6}\.viirs\.npp\.afwa_ops\.[^.]*\.incomplete_[a-z]{3}\.[^.]*\.*\.tdf'),
#    #          re.compile('[0-9]{8}\.[0-9]{6}\.viirs\.npp\.noaa_ops\.[^.]*\.incomplete_[a-z]{3}\.[^.]*\.*\.tdf'),
#    #          re.compile('[0-9]{8}\.[0-9]{6}\.viirs\.npp\.cspp_dev\.[^.]*\.incomplete_[a-z]{3}\.[^.]*\.*\.tdf'),
#    #          re.compile('.*'),
#    #         ]
#    for fname in fnames:
#        prec = None
#        sind = 0
#        while prec is None:
#            if search[sind] is not None:
#                prec = sind
#        precedence.append(prec)
#    return precedence

def process_overpass(satellite,
                     sensor,
                     productlist,
                     sectorlist,
                     sectorfiles,
                     extra_dirs,
                     sector_file,
                     datelist,
                     hourlist=None,
                     data_outpath=None,
                     product_outpath=None,
                     list=False,
                     clean=False,
                     forceclean=False,
                     download=False,
                     queue=None,
                     mp_max_cpus=1,
                     allstatic=True,
                     alldynamic=True,
                     tc=False,
                     volcano=False,
                     quiet=False,
                     start_datetime = None,
                     end_datetime = None,):

    if quiet:
        log.setLevel(35)

    log.interactive('')

    opasses = []
    old_opasses = []
    overall_start_dt = None
    overall_end_dt = None
    single = False
    both = False
    if sectorlist:
        single = True
        both = False
    if hourlist == None:
        for datestr in datelist:
            if sectorlist:
                log.interactive('Checking for overpasses $GEOIPS/geoips/process_overpass.py '+satellite+' '+sensor+' '+datestr+' -s "'+' '.join(sectorlist)+'" --all')
            else:
                log.interactive('Checking for overpasses $GEOIPS/geoips/process_overpass.py '+satellite+' '+sensor+' '+datestr+' --all')
            sys.stdout.write('.')
            sys.stdout.flush()
            start_dt = datetime.strptime(datestr+'0000','%Y%m%d%H%M')
            end_dt= datetime.strptime(datestr+'2359','%Y%m%d%H%M')
            opasses.extend(pass_prediction([satellite],[sensor],sector_file,sectorlist,start_dt-timedelta(minutes=15),end_dt+timedelta(minutes=15),single=single,both=both,force=True,quiet=quiet))
        sys.stdout.write('\n')
        if opasses and len(opasses) < 200 and len(opasses) != 0:
            log.interactive('Available overpasses: '+bigindent+bigindent.join(sorted(str(val) for val in opasses))+'\n')
        elif opasses:
            log.interactive(str(len(opasses))+' available overpasses, not listing\n')
   
        return opasses
    else:
        hourstart = hourlist[0]
        if len(hourlist) == 1:
            hourend = hourlist[0]
        else:
            hourend = hourlist[-1]
        for datestr in datelist:
            if sectorlist and hourlist:
                log.interactive('Checking for overpasses for $GEOIPS/geoips/process_overpass.py '+satellite+' '+sensor+' '+datestr+' -H "'+' '.join(hourlist)+'" -s "'+' '.join(sectorlist)+'" --all')
            else:
                log.interactive('Checking for overpasses for $GEOIPS/geoips/process_overpass.py '+satellite+' '+sensor+' '+datestr+' --all')
            sys.stdout.write('.')
            sys.stdout.flush()
            start_dt = datetime.strptime(datestr+hourstart+'00','%Y%m%d%H%M')
            start_dt = start_dt - timedelta(minutes=15)
            if overall_start_dt == None or overall_start_dt > start_dt:
                overall_start_dt = start_dt
            end_dt = datetime.strptime(datestr+hourend+'59','%Y%m%d%H%M')
            end_dt = end_dt + timedelta(minutes=15)
            if overall_end_dt == None or overall_end_dt < end_dt :
                overall_end_dt = end_dt
            opasses.extend(pass_prediction([satellite],[sensor],sector_file,sectorlist,start_dt,end_dt,single=single,force=True,quiet=quiet))

    sys.stdout.write('\n')

    if opasses and len(opasses) < 20:
        log.interactive('Available overpasses: '+bigindent+bigindent.join(sorted(str(val) for val in opasses))+'\n\n')
    elif opasses:
        log.interactive(str(len(opasses))+' available overpasses, not listing\n\n')


    # Start 8h before start time to make sure we can get the 
    # sector file entry before
    if sensor != 'modis':
        overall_start_dt = overall_start_dt - timedelta(minutes=480)
    log.info('Overall start and end times: '+str(overall_start_dt)+' to '+str(overall_end_dt))

    #if download == True:
    #    log.interactive('queue: '+str(queue)+'\n\n')
    #    data_type = default_data_type[sensor]
    #    host_type = default_host_type[data_type]
    #    #Can't we do something to minimize the copypaste done here?  Hard to maintain...
    #    if (data_type,host_type) in non_qsubbed:
    #        for opass in opasses:
    #            log.info('sectorfiles: '+str(sectorfiles))
    #            sector_file = sectorfile.open(
    #                    allstatic=allstatic,
    #                    alldynamic=alldynamic,
    #                    tc=tc,
    #                    start_datetime = opass.startdt-timedelta(hours=6),
    #                    end_datetime = opass.enddt,
    #                    one_per_sector=True)
    #            if not sectorfiles:
    #                currsectorfiles = sector_file.names
    #            else:
    #                currsectorfiles = sectorfiles
    #            log.info('currsectorfiles: '+str(currsectorfiles))
    #            log.interactive('Downloading opass: '+str(opass)+'\n\n')
    #            si = SatSensorInfo(satellite,sensor)
    #            # If they are very long files (ie, full orbit), make
    #            # sure we get the file before the overpass time
    #            startdt = opass.startdt-timedelta(minutes=si.mins_per_file)
    #            downloader(data_type,host_type,
    #                sector_file=sector_file,
    #                sectorlist=sectorlist,
    #                sectorfiles = currsectorfiles,
    #                productlist=productlist,
    #                data_outpath=data_outpath,
    #                product_outpath=product_outpath,
    #                start_datetime=startdt,
    #                end_datetime=opass.enddt,
    #                queue=queue,
    #                allstatic=allstatic,
    #                alldynamic=alldynamic,
    #                tc=tc,
    #                volcano=volcano,
    #                #max_connections=8,
    #                max_wait_seconds=None,
    #                )
    #            time.sleep(5)
    #    else:
    #        log.interactive(sectorfiles)
    #        downloader(data_type,host_type,
    #            sector_file=sector_file,
    #            sectorlist=sectorlist,
    #            sectorfiles = sectorfiles,
    #            productlist=productlist,
    #            data_outpath=data_outpath,
    #            product_outpath=product_outpath,
    #            start_datetime=overall_start_dt,
    #            end_datetime=overall_end_dt,
    #            queue=queue,
    #            allstatic=allstatic,
    #            alldynamic=alldynamic,
    #            tc=tc,
    #            opasses=opasses,
    #            #max_connections=8,
    #            max_wait_seconds=None,
    #            )
    #        time.sleep(5)

    all_files = []
    # Reverse=True for newest first
    all_files = sorted(find_available_data_files(opasses,start_dt,satellite,sensor,extra_dirs),reverse=True)
    log.info('Done sorting default')
    #shell()
    if productlist and 'near-constant-contrast' in productlist:
        log.info('    Checking near-constant-contrast files')
        # Reverse=True for newest first
        all_files = sorted(find_available_data_files(opasses,start_dt,satellite,sensor,extra_dirs,prodtype='ncc'),reverse=True)
    
    file_str = '\n\t'.join(all_files)
    log.info('Files found current search time for %s: \n\t%s' % (str(opasses),file_str))

    if not all_files:
        log.info('No files available in directories listed above')
        log.info('To check alternate directories, you can call (replace /sb2/viirs and /sb1/viirs with the paths where data files are available): ')
        infostr = ''
        if productlist:
            infostr+='-p '+"'"+' '.join(productlist)+"'"
        if sectorlist:
            infostr+='-s '+"'"+' '.join(sectorlist)+"'"
        log.info("process_overpass.py %s %s '%s' -d '/sb2/viirs /sb1/viirs' %s -H '%s'"%(
                satellite,
                sensor,
                ' '.join(datelist),
                infostr,
                ' '.join(hourlist)))

        return None

    try:
        for opass in opasses:
            currdatelist = []
            day_count = (opass.enddt - opass.startdt).days + 1
            for dt in (opass.startdt+timedelta(n) for n in range(day_count)):
                currdatelist.append(dt.strftime('%Y%m%d'))
            log.info('Checking for existing products to clean... clean: '+str(clean)+' forceclean: '+str(forceclean))
            find_existing_products(sensor,sector_file,opass.actualsectornames,productlist,currdatelist,clean,forceclean)
    except ProductError,resp:
        log.error(str(resp)+' Check spelling?')
#        return None
#            if files:

    
    if list == False:
        file_num = 0
        for file in all_files:
            file_num = file_num+1 
            log.interactive('\n\n\n')
            log.interactive('Starting processing for file '+str(file_num)+' of '+str(len(all_files))+': '+file+'\n\n')
            if os.path.isdir(file):
                try:
                    dfn = DataFileName(glob(file+'/*')[0])
                except IndexError:
                    log.interactive('    Appear to be no data files in directory !! Skipping')
                    continue
            else:
                dfn = DataFileName(os.path.basename(file))
            dt = dfn.datetime
            if start_datetime and (dfn.datetime < start_datetime or dfn.datetime > end_datetime):
                log.interactive('Outside of time range, skipping')
                continue
            currsectorlist = []
            if not sectorlist:
                curropasses = pass_prediction([dfn.satname],[dfn.sensorname],sector_file,sectorlist,dt-timedelta(minutes=15),dt+timedelta(minutes=15),single=True,quiet=quiet)
                for opass in curropasses:
                    log.info(opass)
                    if dfn.is_concurrent_with(opass.startdt,dt,opass.enddt):
                        log.interactive('Overlaps overpass '+str(opass.opass))
                        currsectorlist.extend(opass.actualsectornames)
            else:
                currsectorlist = sectorlist
            #log.interactive('process_overpass sectorfiles: '+str(sectorfiles))
            #log.interactive('process_overpass currsectorlist: '+str(currsectorlist))
               
            #log.interactive('Data file date: '+fileobj.date) 
            #log.interactive('Data file: '+fileobj.name)
            pfile = ProductFileName()
            pfile.date = dt.strftime('%Y%m%d')
            pfile.time = dt.strftime('%H%M%S')
            pfile.satname = dfn.sensorinfo.satname
            pfile.sensorname = dfn.sensorinfo.sensorname
            #print len(currsectorlist)
            if len(currsectorlist) == 1:
                pfile.sector_name = currsectorlist[0]
            logfile = pfile.create_logfile()
            log.info('Using logfile: '+logfile.name)
            #logfile.makedirs()

            asterisks = '*'*60
            #cmd = 'source /users/surratt/nrlsat/config/standard_bashrc branch surratt 0.3.0; python '+gpaths['GEOIPS']+'/driver.py'
            cmd = 'python '+gpaths['GEOIPS']+'/geoips/driver.py'
            #Build array of command options
            cmd_args = CMDArgs()
            cmd_args.addarg(file)
            # We only need to pass the sectorfile that actually contains this 
            # sector - don't pass all sectorfiles that we are using in gendriver 
            # (which could include all dynamic sectorfiles, and all static...)
            start_dt = dt - timedelta(hours=9)
            #if not fileobj.end_dt:
            #    end_dt = fileobj.start_dt+ timedelta(minutes=15)
            #else:
            #    end_dt = fileobj.end_dt
            end_dt = dt + timedelta(minutes=15)
            actual_dt = start_dt
            currsf = sectorfile.open(
                    sectorfiles=sectorfiles,
                    allstatic=allstatic,
                    alldynamic=alldynamic,
                    tc=tc,
                    volcano=volcano,
                    start_datetime = start_dt,
                    end_datetime = end_dt,
                    actual_datetime = actual_dt,
                    sectorlist=currsectorlist,
                    one_per_sector=True)
            if currsf.names: cmd_args.addopt('sectorfiles', ' '.join(currsf.names))
            if productlist: cmd_args.addopt('productlist', ' '.join(productlist))
            if currsectorlist: cmd_args.addopt('sectorlist', ' '.join(currsectorlist))
            if tc: cmd_args.addopt('tc')
            if volcano: cmd_args.addopt('volcano')
            if allstatic: cmd_args.addopt('allstatic')
            if alldynamic: cmd_args.addopt('alldynamic')
            cmd_args.addopt('forcereprocess')
            cmd_args.addopt('queue', queue)
            # pass mp_max_cpus to process_overpass.py, then pass to driver.py.
            cmd_args.addopt('mp_max_cpus', str(mp_max_cpus))
            cmd_args.addopt('loglevel', 'info')
            gendriver_call = '%s %s' % (cmd, cmd_args)

            log.info('Manual driver.py call: \n'+gendriver_call)
            log.info('Logfile: \t'+logfile.name)
            log.info('queue: \t'+str(queue))


            if queue != None:
                #wait_for_queue(job_names=[],max_num_jobs=450,max_num_cnvrt_jobs=15,max_other_jobs_dict={'PO'+logfile.qsubclassifier:10})
                while True:
                    # Keep going if we reach maximum recursion depth, which appears to be like 980 ?  
                    try:
                        wait_for_queue(job_limits_RandQ={'PO':10},job_limits_Ronly={},max_total_jobs=400,max_user_jobs=10)
                        break
                    except RuntimeError:
                        continue
                    
                log.interactive('Kicking off qsub')
                # pass mp_max_cpus to process_overpass.py, then pass to driver.py.
                # Estimating 2.5gb per cpu... need to check on that...
                # Need int for mem. round up.
                resource_list = 'nodes=1:ppn='+str(mp_max_cpus)+',mem='+str(int(mp_max_cpus*5 + .5))+'gb'
                qsub(cmd, 
                             cmd_args.get_arglist(),
                             queue=queue,
                             name='PO'+logfile.qsubname,
                             resource_list=resource_list,
                             outfile=str(logfile),
                             join=True
                            )
                #if os.path.isfile(logfile.name):
                #    os.system('grep INTERACTIVE '+logfile.name)
            else:
                df = SciFile()
                df.import_data([file])

                from driver import driver
                cleanup_files = driver(df,
                                                currsf,
                                                sectorlist=sectorlist,
                                                productlist=productlist,
                                                forcereprocess=True
                                               )

        log.interactive('\n'+asterisks+'\n')
        currdatelist = []
        day_count = (opass.enddt - opass.startdt).days + 1
        for dt in (opass.startdt+timedelta(n) for n in range(day_count)):
            currdatelist.append(dt.strftime('%Y%m%d'))
        find_existing_products(sensor,currsf,opass.actualsectornames,productlist,currdatelist,clean=False,forceclean=False)

def _get_argument_parser():
    '''Create an argument parser with all of the correct arguments.'''
    # Need RawTextHelpFormatter for \n to work.
    parser = ArgParse(formatter_class=argparse.RawTextHelpFormatter,description=
        'Wrapper for processing an entire overpass based on date/time.\n'+\
        'satellite, sensor, product, sector, date, and time are required.\n')
    from geoips.utils.satellite_info import all_available_satellites,all_sensors_for_sat
    values = []
    allsensors = productfile.get_sensornames()
    # Getting list of sat/sensors
    for sat in all_available_satellites():
        for sensor in all_sensors_for_sat(sat):
            if sensor in allsensors:
                values.append(sat+' '+sensor)
    parser.add_argument('satellite', help='Single satellite name')
    parser.add_argument('sensor', help='Single sensor name. Uses the following possible satellite/sensor pairs:\n'+\
                                '\n'.join(['SATSENSORPAIR '+val for val in values])+'\n\n')
    parser.add_argument('datelist',
                        help="'YYYYMMDD YYYYMMDD YYYYMMDD' or YYYYMMDD-YYYYMMDD")
    parser.add_argument('-H','--hourlist',nargs='?',default=None,
                        help="'HH HH HH' or 'HH-HH'")
    parser.add_arguments([
                        'productlist',
                        'sectorlist',
                        'sectorfiles',
                        'all',
                        'allstatic',
                        'alldynamic',
                        'volcano',
                        'tc',
                        'list',
                        'extra_dirs',
                        'queue',
                        'mp_max_cpus',
                        'clean',
                        'forceclean',
                        'download',
                        ])
    parser.add_argument('-l','--loglevel',default='INTERACTIVE',
                        help='Specify log level: error, warning, info, interactive, debug.\n\n'
                        )
    return parser


if __name__ == '__main__':
    # Set all these to None for uncaught exception handling
    emailsubject = "process_overpass"
    email_hndlr = None
    root_logger = None
    combined_sf = None
    args = {'satellite': None,'sensor':None,'sectorfiles':[],'productlist':None,'sectorlist':None}

    # Wrap everything in try/except, so if there is an uncaught exception, 
    # it gets emailed to me
    try:
        parser = _get_argument_parser()
        args = vars(parser.parse_args())
        #print args
        root_logger,file_hndlr,email_hndlr = root_log_setup(loglevel=args['loglevel'],subject=emailsubject)
        args=parser.cleanup_args(args)
        #log.interactive('clean: '+str(args['clean'])+' forceclean: '+str(args['forceclean']))

        datelist = None
        hourlist = None
        
        # Allow for range of dates to process, use startdate and enddate in sectorfile.open
        if '-' in args['datelist']:
            startdate,enddate = args['datelist'].split('-')
            startdt = datetime.strptime(startdate,'%Y%m%d')
            enddt = datetime.strptime(enddate,'%Y%m%d')
            datelist = []
            day_count = (enddt - startdt).days + 1
            for dt in (startdt+timedelta(n) for n in range(day_count)):
                datelist.append(dt.strftime('%Y%m%d'))
        else:
            # Allow for list of dates, set startdate and enddate for use in sectorfile.open
            datelist = args['datelist'].split()
            largest = 00000000
            smallest = 99999999
            for date in datelist:
                if int(date) < smallest:
                    smallest = date
                if int(date) > largest:
                    largest = date 
            startdate = str(smallest)
            enddate = str(largest)
            log.info('startdate: '+startdate+' enddate: '+enddate)

        # Allow for range or list of hours to process
        if args['hourlist'] != None and '-' in args['hourlist']:
            starthour,endhour = args['hourlist'].split('-')
            hours = range(int(starthour),int(endhour))
            hourlist = []
            for hour in hours:
                hourlist.append('%02d'%hour)
        elif args['hourlist'] != None:
            hourlist = args['hourlist'].split()

        if args['all'] == True:
            args['allstatic'] = True
            args['alldynamic'] = True

        # Find appropriate dynamic and static sectorfiles. 
        start_dt = datetime.strptime(startdate+'0000','%Y%m%d%H%M')
        start_dt = start_dt - timedelta(minutes=15)
        end_dt = datetime.strptime(enddate+'2359','%Y%m%d%H%M')
        end_dt = end_dt + timedelta(minutes=15)
        log.info('start_dt: '+str(start_dt))
        log.info('end_dt: '+str(end_dt))
        for datestr in datelist:
            log.info('datestr: '+str(datestr))
            start_dt = datetime.strptime(datestr+'0000','%Y%m%d%H%M')
            start_dt = start_dt - timedelta(minutes=15)
            end_dt= datetime.strptime(datestr+'2359','%Y%m%d%H%M')
            end_dt = end_dt + timedelta(minutes=15)
            sys.stdout.write('\n')
            # Need all dynamic sector files for the whole day for pass prediction (one_per_sector = False)
            sector_file = sectorfile.open(
                    sectorfiles=args['sectorfiles'],
                    allstatic=args['allstatic'],
                    alldynamic=args['alldynamic'],
                    tc=args['tc'],
                    volcano=args['volcano'],
                    start_datetime = start_dt,
                    end_datetime = end_dt,
                    sectorlist=args['sectorlist'],
                    one_per_sector=False)
            #log.info(sector_file.names)

            try:
                # This checks the opened sectors for duplicates, and checks the passed sectorlist and productlist for invalid entries
                #sector_file.check_sectorfile(sectorlist=args['sectorlist'],productlist=args['productlist'])
                if not args['sectorlist']:
                    if args['tc'] or args['volcano'] or args['alldynamic']:
                        sectorlist = [x.lower() for x in sector_file.sectornames()]
                    else:
                        sectorlist = None
                else:
                    sectorlist = args['sectorlist']
                if not args['sectorfiles']:
                    # This is screwing up reprocessing TCs... passes all the sectorfiles to gendriver
                    #sectorfiles = sector_file.names
                    sectorfiles = []
                else:
                    sectorfiles = args['sectorfiles']
                #log.info('sectorfiles in process_overpass: '+str(sectorfiles))
                #log.info('sectorlist in process_overpass: '+str(sectorlist))
                process_overpass(args['satellite'],
                                 args['sensor'],
                                 args['productlist'],
                                 sectorlist,
                                 sectorfiles,
                                 args['extra_dirs'],
                                 sector_file,
                                 [datestr],
                                 hourlist=hourlist,
                                 list=args['list'],
                                 clean=args['clean'],
                                 forceclean=args['forceclean'],
                                 download=args['download'],
                                 queue=args['queue'],
                                 mp_max_cpus=int(args['mp_max_cpus']),
                                 allstatic=args['allstatic'],
                                 alldynamic=args['alldynamic'],
                                 tc=args['tc'],
                                 volcano=args['volcano']
                                )
            except SectorFileError,resp:
                log.interactive('')
                log.interactive('')
                log.error(str(resp))
                log.interactive('Invalid sector options (Check --sectorfiles, -s, -p)')
                if args['all'] == True:
                    sector_file = sectorfile.open(
                        allstatic=True,
                        alldynamic=True,
                        start_datetime = start_dt,
                        end_datetime = end_dt,
                        one_per_sector=True)
                else:
                    sector_file = sectorfile.open()
                sector_file.check_sectorfile()
                log.interactive(' Remember to call with --all if you want dynamic sectors')
                log.interactive('')
                log.interactive('')

    # except Exception shouldn't catch KeyboardInterrupt and SystemExit
    except Exception:
        uncaught_exception(root_logger,
                    email_hndlr,
                    subject='uncaught '+emailsubject,
                    file=str(args['satellite'])+str(args['sensor']),
                    sectorfiles=args['sectorfiles'],
                    productlist=args['productlist'],
                    sectorlist=args['sectorlist'],
                    combined_sf=combined_sf,
                    )
