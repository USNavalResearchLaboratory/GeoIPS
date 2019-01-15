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
import commands
import ftplib
import socket
import logging
import os
import shutil
from glob import glob
from datetime import timedelta,datetime
from subprocess import Popen, PIPE

# Installed Libraries
from IPython import embed as shell

# GeoIPS Libraries
from ..downloaderrors import DownloaderGiveup
from geoips.pass_prediction.pass_prediction import pass_prediction
from geoips.utils.cmdargs import CMDArgs
from geoips.utils.log_setup import interactive_log_setup
from geoips.utils.qsub import qsub
from geoips.utils.path.datafilename import DataFileName
from geoips.utils.decorators import TimeoutError
from geoips.utils.plugin_paths import paths as gpaths

log = interactive_log_setup(logging.getLogger(__name__))

class Site(object):
    '''Class defining an ftp or http connection'''
    def __init__(self,
                 host,
                 downloadactive=True,
                 queue=None,
                 **kwargs
                ):
        self.host = host
        self.downloadactive = downloadactive
        self.queue = queue
        self.pp_args = CMDArgs()
        log.info('host %s, downloadactive %s' % (self.host,str(self.downloadactive)))

    def quit_connection(self):
        if hasattr(self,'sftp'):
            self.con.close()
        else:
            try:
                self.con.quit()
            except (ftplib.error_temp),resp:
                log.error(str(resp)+':  Failed closing the connection with ftplib.error_temp... Lets just ignore that')      
            except (socket.error),resp:
                log.error(str(resp)+':  Failed closing the connection with socket.error... Lets just ignore that')      
            except AttributeError:
                pass

    # Override this is child class if you have to login for specific connection type.
    def login(self,timeout=None):
        return None

    def daterange(self,start_date,end_date):
        '''Check one day at a time when looking for new remote data files'''
        # If end_date - start_date is between 1 and 2, days will be 1, 
        # and range(1) is [0].  So add 2 to days to set range. (+1 would still fail sometimes)
        for n in range((end_date - start_date).days + 2):
            yield start_date + timedelta(n)

    def hourrange(self,start_date,end_date):
        '''Check one hour at a time when looking for new remote data files'''
        log.info('in hourrange')
        log.info((end_date - start_date).seconds)
        tr = end_date - start_date
        for n in range((tr.days * 24 + tr.seconds / 3600) + 1):
            yield start_date + timedelta(seconds = (n * 3600))

    def clean_duplicates(self,localfile):
        '''Can override this in subclasses to force cleaning of duplicate files.'''
        log.info('      *** No duplicate cleaning on {0} / {1}'.format(self.host_type,self.data_type)) 
        return False

    def clean_duplicates_on_check(self,localfile,remotefile):
        '''Can override this in subclasses to force cleaning of duplicate files on the
            just_check_if_all_downloaded phase. This is mostly used for the localdata 
            downloader type and will basically catch files that
            didn't get moved out of place because 2 processes were trying to move
            them at the same time. Next time through this will delete the original '''
        log.info('      *** No duplicate cleaning during the "clean_duplicate_on_check" phase on {0} / {1}'.format(self.host_type,self.data_type))
        return False

    def convert(self,file,final_filename):
        '''The convert method is called from the postproc method. The default
        method in Site.py just moves from file to final_filename. If there are
        actual conversions that have to happen, this will likely be overriden
        in the subclasses of Site ([host_type].py, [host_type]_[data_type].py)'''

        log.info('Using Site convert')
        dfn = DataFileName(os.path.basename(file))

        if os.path.isfile(file):
            # if file is gzipped, unzip first
            if hasattr(self,'untgzfiles') and self.untgzfiles and ('tar.gz' in dfn.ext or 'tgz' in dfn.ext):
                log.info('   ****untgzing file '+file)
                return self.untgz(file)
            elif hasattr(self,'unbz2files') and self.unbz2files and ('.bz2' in dfn.ext):
                log.info('   ****bunzip2 file '+file)
                retval = os.system('bunzip2 '+file)
                log.info('   ****moving file to '+final_filename)
                if os.path.isfile(os.path.splitext(file)[0]):
                    shutil.move(os.path.splitext(file)[0],final_filename)
                    return [final_filename]
                elif retval != 0:
                    log.info('    ****Final file failed!')
                    return []
            elif 'gz' in dfn.ext and 'tgz' not in dfn.ext:
                log.info('   ****gunzipping file '+file)
                retval = os.system('gunzip '+file)
                log.info('   ****moving file to '+final_filename)
                if os.path.isfile(os.path.splitext(file)[0]):
                    shutil.move(os.path.splitext(file)[0],final_filename)
                    return [final_filename]
                elif retval != 0:
                    log.info('    ****Final file failed!')
                    return []
            else:
                log.info('   ****moving file to '+final_filename)
                shutil.move(file,final_filename)
                return [final_filename]
        else:
            log.info('File '+file+' does not exist, not moving')
            return []

    def get_final_ext(self):
        ''' This allows you to change the extension on the final filename.
            if the extension does not change, return None. If the extension 
            changes, override get_final_ext in subclass'''
        return None

    def get_final_filename(self,file):
        '''Eventually this will be standard for everything in Site.py
        for now test with rscat/viirs only. This returns a string'''
        fn = DataFileName(os.path.basename(file))
        sdfn = fn.create_standard(downloadSiteObj=self)
        if self.get_final_ext():
            sdfn.ext = self.get_final_ext()
        return sdfn.name

    def get_filenamedatetime(self,file):
        '''Eventually this will be standard for everything in Site.py
        for now test with rscat/viirs only. This returns a datetime
        object, not a FileName object.'''
        fn = DataFileName(os.path.basename(file))
        if fn:
            sfn = fn.create_standard(downloadSiteObj=self)
        else:
            return None
        return sfn.datetime

    def get_logfname(self,file,geoips=True,postfix=None):
        if os.path.isdir(file):
            dfn = DataFileName(os.path.basename(glob(file+'/*')[0]))
        else:
            dfn =  DataFileName(os.path.basename(file))
        sdfn = dfn.create_standard(downloadSiteObj=self)
        return sdfn.create_logfile(geoips=geoips)

    def run_on_files(self,file):
        return [file]

    def pre_legacy_procs(self,final_file):
        return True

    def get_opasses(self,file,sectorfiles=None):
        log.info('Running pass predictor on: '+str(file))
        # Paths sometimes mess this up. Use os.path.basename
        fn = DataFileName(os.path.basename(file))
        sfn = fn.create_standard(downloadSiteObj=self)
        if sectorfiles:
            opasses = pass_prediction([sfn.satname],
                        [sfn.sensorname],
                        None,
                        None,
                        sfn.datetime-timedelta(hours=9),
                        sfn.datetime,
                        single=True,
                        force=True,
                        sectorfiles=sectorfiles)
        elif self.sector_file:
            opasses = pass_prediction([sfn.satname],
                        [sfn.sensorname],
                        self.sector_file,
                        self.sectorlist,
                        sfn.datetime-timedelta(hours=9),
                        sfn.datetime,
                        force=True,
                        single=True)
        else:
            opasses = pass_prediction([sfn.satname],
                        [sfn.sensorname],
                        None,
                        None,
                        sfn.datetime-timedelta(hours=9),
                        sfn.datetime,
                        force=True,
                        single=True)
        return opasses

    def opass_overlaps(obj,opass,fnstr):
        '''Eventually this will be standard for everything in Site.py
        for now test with rscat/viirs only. '''
        # Paths sometimes mess this up. Use os.path.basename
        fn = DataFileName(os.path.basename(fnstr))
        sfn = fn.create_standard(downloadSiteObj=obj)
        sfn_enddt = sfn.datetime + timedelta(minutes=fn.sensorinfo.mins_per_file)
        #log.info('opass: '+str(opass)+'sfn: '+str(sfn)+' sfn_enddt: '+str(sfn_enddt))
        overlaps = sfn.is_concurrent_with(opass.startdt,sfn.datetime,opass.enddt,sfn_enddt)
        #log.info('overlaps: '+str(overlaps))
        return overlaps

    def postproc(self,file,geoips_args=None,forceprocess=False,noprocess=False):
        '''The postproc method is called from downloaders.Sites.Site.get
            After a file has been successfully downloaded, postproc is 
            called on that file to do any necessary conversions, post
            processing, etc. 
            This should not be overridden in the subclasses, but methods that are
                called from postproc can be overridden to customize:

            run_on_files:
                Check for existence of certain files before kicking off processing
                Also can put in pre-geoips processing steps in here (to either run on
                    individual file, or group of files. Note this runs serially, so 
                    don't put anything in here that takes a long time!)
            convert:
                perform special conversions (by default gunzips and moves to final_filename)
            get_final_filename:
                by default uses GeoIPS standard data filename (can override to use original, etc)
            pre_legacy_procs:
                No one uses this - called before ppscript, if returns True, then run ppscript
                Defaults to just returning True
            pp_script:
                attribute set on subclass that is the legacy postprocs call. 
                If set, pp_script will be run
        '''


        final_filename = self.get_final_filename(file)


        #log.info('Using Site postproc')

        # The default version of this (found above in Site.py) just moves 
        # file to final_filename. Can be overriden in host/data classes
        # to actually convert the file, not just change filename...
        if not glob(final_filename) or forceprocess:
            if forceprocess:
                log.interactive('Force running convert/process (called immediately after successful download?)')
            else:
                log.interactive('Final file: '+final_filename+' did not exist, reconverting/reprocessing')

            # convert method returns a list of files that need processing -
            # amsu converter, for instance, creates multiple files from a 
            # single input file
            for final_file in self.convert(file,final_filename):
                if noprocess:
                    log.info('SKIPPING processing on file, downloader called with --noprocess '+final_file)
                    continue
                # If self.pp_script is defined in [host_type].py or 
                # [host_type]_[data_type].py, run postprocs
                runpp = True
                try:
                    log.info('   ****qsubbing '+os.path.basename(self.pp_script)+' '+final_file)
                except (NameError,AttributeError):
                    log.info('   ****No non-GeoIPS postprocs defined')
                    runpp = False
                if runpp:
                    for file in self.run_on_files(final_file):
                        log.info('    ****Running non-GeoIPS postprocessing on '+os.path.basename(file))
                        if self.pre_legacy_procs(file):
                            # pp_script may have arguments, so split on spaces and just use the
                            # basename of the first argument (script name) for logname
                            log_fname = self.get_logfname(file,geoips=False)
                            log_fname.makedirs()
                            resource_list = None
                            qsub(self.pp_script+' '+file+os.getenv('LEGACY_PROCSDIR_CALL_AFTER'),
                                         [],
                                         queue=self.queue,
                                         name=log_fname.qsubname,
                                         resource_list=resource_list,
                                         outfile=log_fname.name,
                                         suffix='log'
                                        )



                dfn = DataFileName(os.path.basename(final_file))
                sdfn = dfn.create_standard(downloadSiteObj=self)

                if self.run_geoips == True:
                    # self.run_on_files defaults to returning final_file
                    # can override run_on_files function in host_type/data_type 
                    # subclass (ie, for modis where we must have a specific
                    # set of files before we can run driver)
                    for file in self.run_on_files(final_file):
                        log_fname = self.get_logfname(file)
                        log_fname.makedirs()
                        log.info(log_fname.name)
                        # geoips_args are set in downloader based on sector_file information (static vs dynamic),
                        # and passed arguments for sectorfiles / sectorlist.
                        # Do NOT run pass predictor in downloader anymore - now it is run in driver.
                        # but we still need to make sure we allow for passing a list of sectors to downloader...

                        if not geoips_args:
                            #arglist = [file,'--queue batch@kahuna','-s "'+' '.join(sectorlist)+'"']
                            arglist = [file,'--queue batch@kahuna']
                            # Currently setting mp_max_cpus and mp_mem_per_cpu in individual Site inits
                            if hasattr(self,'mp_max_cpus'):
                                arglist+= ['--mp_max_cpus '+str(int(self.mp_max_cpus))]
                        else:
                            dfn = DataFileName(os.path.basename(file))
                            if dfn.sensorinfo.FName['runfulldir']:
                                geoips_args.addarg(os.path.dirname(file))
                            else:
                                geoips_args.addarg(file)
                            log.info(geoips_args.options)
                            # Currently setting mp_max_cpus and mp_mem_per_cpu in individual Site inits
                            if hasattr(self,'mp_max_cpus'):
                                geoips_args.addopt('mp_max_cpus',str(int(self.mp_max_cpus)))
                            arglist = geoips_args.get_arglist()
                            # Remove the file we just added so we can 
                            # add the next one
                            geoips_args.delarg(0)

                        # Currently setting mp_max_cpus and mp_mem_per_cpu in individual Site inits
                        if hasattr(self,'mp_max_cpus'):
                            resource_list = os.getenv('PBS_RESOURCE_LIST_SELECT')+str(int(self.mp_max_cpus))+\
                                            os.getenv('PBS_RESOURCE_LIST_MEM')+str(int(self.mp_mem_per_cpu*self.mp_max_cpus))+'gb'+\
                                            os.getenv('PBS_RESOURCE_LIST_QLIST')
                        else:
                            resource_list = None

                        if hasattr(self,'geoips_executable'):
                            geoips_executable = self.geoips_executable
                        else:
                            geoips_executable = gpaths['GEOIPS']+'/geoips/driver.py'

                        qsub(geoips_executable,
                                     arglist,
                                     queue=self.queue,
                                     #name='GW'+self.data_type+'_'+self.host_type,
                                     name=log_fname.qsubname,
                                     resource_list=resource_list,
                                     outfile=log_fname.name
                                    )

    def set_local_subdir(self,remotefile):
        '''Return empty string for local subdir, because when using new 
        DataFileName objects, full path is included in create_standard'''
        return ''

    def find_files_in_range(self,files,start_time,end_time,urlpath=None):
        getfiles = []
        log.info('Finding files matching requested time out of '+str(len(files))+' files...')
        for file in files:  
            dt = self.get_filenamedatetime(file)
            if dt is None:  
                log.info('    Skipping file, does not match file name format '+file)
            elif (dt <= end_time and dt >= start_time):
                if urlpath != None:
                    file = urlpath+'/'+file
                #log.debug('    file matches: '+file+' '+str(dt)+' '+str(start_time)+' '+str(end_time))
                #log.info('    file matches: '+os.path.basename(file))
                getfiles.append(file)

        getfiles.reverse()

        if getfiles == []:
            log.info('No files found between '+str(start_time)+' and '+str(end_time))

        return getfiles

    def files_exist(self,files):
        exist = True
        for file in files:
            if not glob(file):
                #print ' not there '+file
                exist = False
        return exist

    # This method can be overriden in any subclass:
    # not currently overriden in HTTPSite or FTPSite (but could be)
    def file_exists(self,localfile):
        #log.info('Using Site file_exists')

        final_filename = self.get_final_filename(localfile)
        #log.info(final_filename)

        #log.info('Sfinal_filename: '+str(final_filename))

        # This covers original download name
        if os.path.isfile(localfile) == True:
            log.info('SFile exists: '+localfile)
            return localfile
        elif os.path.isfile(localfile+'.processing') == True:
            file_timestamp = datetime.fromtimestamp(os.stat(localfile+'.processing').st_mtime)
            currdt = datetime.now()
            max_timediff = timedelta(hours=3)
            log.info('Sprocessing file exists: '+localfile+'.processing'+' file ts: '+str(file_timestamp)+' timediff: '+str(currdt - file_timestamp)+' max timediff: '+str(max_timediff))
            # If the .processing file is really old, assume it failed, download again.
            if (currdt - file_timestamp) > max_timediff:
                log.warning('        Sprocessing file older than '+str(max_timediff)+', try again')
            else:
                return localfile+'.processing'
        # This covers our final standardized filename 
        elif os.path.isfile(final_filename) == True:
            log.info('SFinal filename exists: '+final_filename)
            return final_filename
        elif os.path.isfile(final_filename+'.processing') == True:
            log.info('Sfinal processing file exists: '+final_filename+'.processing')
            return final_filename+'.processing'
        # This covers files that need to be unzipped on arrival (remove suff)
        elif os.path.isfile(os.path.splitext(localfile)[0]):
            log.info('SFinal unzipped filename exists: '+os.path.splitext(localfile)[0])
            return os.path.splitext(localfile)[0]
        elif os.path.isfile(os.path.splitext(localfile)[0]+'.processing') == True:
            log.info('Sfinal unzipped processing file exists: '+os.path.splitext(localfile)[0]+'.processing')
            return os.path.splitext(localfile)[0]+'.processing'
        # This covers files that need to be unzipped after being moved to final_filename (remove suff)
        elif os.path.isfile(os.path.splitext(final_filename)[0]):
            log.info('SFinal unzipped filename exists: '+os.path.splitext(final_filename)[0])
            return os.path.splitext(final_filename)[0]
        elif os.path.isfile(os.path.splitext(final_filename)[0]+'.processing') == True:
            log.info('Sfinal unzipped processing file exists: '+os.path.splitext(final_filename)[0]+'.processing')
            return os.path.splitext(final_filename)[0]+'.processing'

        return False

    def sort_files(self,filelist):
        '''Override sort_files function found in Site.py. '''
        #print filelist
        #log.info('    Creating list of DataFileName objects to sort')
        newfilelist = [ DataFileName(file) for file in filelist]
        #log.info('        Sorting list')
        newfilelist.sort(cmp,key=lambda x:x.datetime,reverse=True)

        #date_pattern = re.compile('RS.*\.([0-9]{11})') 
        #log.debug('filelist: '+str(filelist))
        #filelist.sort(cmp,key=lambda file:date_pattern.search(file).group(1),reverse=True)
        #log.debug('filelist: '+str(filelist))
        #log.info('        Creating list of string objects to return')
        filelist = [ file.name for file in newfilelist ]
        return filelist

    def set_localfile(self,basename,localdir=None):
        '''Eventually this will be standard for everything in Site.py
        and we won't have to pass localdir/localsubdir
        for now test with rscat only'''
        finalfnstr = self.get_final_filename(basename)
        return os.path.dirname(finalfnstr)+'/'+basename

    def makedirs(self,file):
        dfn = DataFileName(os.path.basename(file))
        sdfn = dfn.create_standard(downloadSiteObj=self)
        sdfn.makedirs()

    def move_to_final(self,temp_file,processing_file,final_file):
        try:
            log.info('      ***      Moving from temp file '+temp_file+' to final file')
            log.info('               '+commands.getoutput('ls --full-time '+temp_file))
            shutil.move(temp_file,processing_file)
            shutil.move(processing_file,final_file)
        except (OSError,IOError),resp:
            if os.path.exists(final_file):
                log.error(str(resp)+'This download failed, someone else must have downloaded the file and already moved it into place: '+final_file)
            else:
                log.error(str(resp)+'Hmm... OSError on the shutil.move, but the final file does not exist... Odd... '+temp_file)
        if os.path.exists(temp_file):
            log.info('Removing '+temp_file)
            os.unlink(temp_file)
        if os.path.exists(processing_file):
            log.info('Removing '+processing_file)
            os.unlink(processing_file)
        try:
            os.chmod(final_file, 0644)
        except OSError:
            log.warning('      Failed chmod, ignore')

    def get(self,filelist,geoips_args=None,just_check_if_all_downloaded=False,overall_fail_minutes=None,total_num_files=None,connect=True,noprocess=False,time_so_far=None,files_so_far=None):

        dt_start_of_download = datetime.utcnow()


        if (not filelist):
            return ['',0]

        #log.info('Sorting files')
        # Just sort alphanumerically be default, can be overriden in subclasses 
        #print filelist
        filelist = self.sort_files(filelist)

        dirs = {} 
        retval = dirs
        numfiles = 0
        if files_so_far:
            numfiles += files_so_far

        # If we're just checking if we have all the files, we don't
        # have to connect - this way we don't need to reserve a 
        # connection for the wrappers...
        if not just_check_if_all_downloaded and connect == True:
            log.info('      *** download from '+self.host)
            self.con = self.login(timeout=20)

        for remotefile in filelist:

            if len(filelist) > 1 or time_so_far:
                currdt = datetime.utcnow()
                timerunning = currdt - dt_start_of_download
                if time_so_far:
                    timerunning += time_so_far
                log.info('')
                log.info('Running for '+str(timerunning)+' so far, '+str(numfiles)+' total files')
            if overall_fail_minutes and timerunning > timedelta(minutes=overall_fail_minutes):
                raise DownloaderGiveup('We\'ve been running for '+str(timerunning)+', quiting altogether')
            if total_num_files and numfiles > total_num_files:
                raise DownloaderGiveup('We\'ve downloaded '+str(numfiles)+' files, quiting altogether')

            #if not just_check_if_all_downloaded:
            #    log.info('      Working on remote: %s' % remotefile)
            log.info('      Working on remote: %s' % remotefile)

            basename = os.path.basename(remotefile)

            #log.info('      basename: %s' % basename)

            try:
                localfile = self.set_localfile(basename)
            except (ValueError,AttributeError):
                if not just_check_if_all_downloaded:
                    log.warning('Invalid filename, skipping '+remotefile)
                log.warning('Invalid filename, skipping '+remotefile)
                continue 

            fulllocaldir = os.path.dirname(localfile)
            #log.info(localfile)

            existinglocalfile = self.file_exists(localfile)
            # file_exists is defined in Site.py, 
            if existinglocalfile != False:
                if '.processing' in existinglocalfile:
                    if not just_check_if_all_downloaded:
                        log.interactive('      *** SKIPPING not downloading %s' % basename) 
                        log.info('      ***   %s.processing is being downloaded' % existinglocalfile)
                else:
                    if not just_check_if_all_downloaded:
                        log.interactive('      *** SKIPPING not downloading %s' % basename) 
                        log.info('      ***   %s already downloaded' % remotefile)
                    if not just_check_if_all_downloaded:
                        self.clean_duplicates(existinglocalfile)
                    else:
                        self.clean_duplicates_on_check(existinglocalfile,remotefile)
                    # This is the postproc found in downloaders/Sites
                    if not just_check_if_all_downloaded:
                        if geoips_args != None:
                            self.postproc(existinglocalfile,geoips_args=geoips_args,noprocess=noprocess)
                        else:
                            self.postproc(existinglocalfile,noprocess=noprocess)
                    dirs[fulllocaldir.strip()] = 1
                    retval = dirs
            else: 
                if just_check_if_all_downloaded == True:
                    log.info('      *** Just checking if all files are already downloadedd - '+
                             'there are new files available! So let\'s kick off downloader!')
                    return False
                self.makedirs(localfile)
                try:
                    log.interactive('      *** working on %s' % localfile) 
                    self.getfile(remotefile,localfile)
                    dirs[fulllocaldir.strip()] = 1
                    retval = dirs
                    log.interactive('      *** SUCCESS Downloaded "%s"' % basename)

                    if geoips_args != None:
                        self.postproc(localfile,geoips_args=geoips_args,forceprocess=True,noprocess=noprocess)
                    else:
                        self.postproc(localfile,forceprocess=True,noprocess=noprocess)
                    numfiles = numfiles + 1
                except (socket.timeout,socket.error,ftplib.error_temp,ftplib.error_perm,TimeoutError),resp:
                    log.error(str(resp)+':  Failed downloading moving onto next file: '+basename)      
                except (OSError,IOError),resp:
                    if os.path.exists(localfile):
                        log.error(str(resp)+' Skipping processing, someone else must have downloaded the file and already moved it into place: '+localfile)
                    else:
                        log.error(str(resp)+' Hmm... Error on the shutil.move, but the final file does not exist... Odd... '+localfile)
            if not just_check_if_all_downloaded:
            	log.info('\n\n')

        if connect == True:
            self.quit_connection()

        return [retval,numfiles]
