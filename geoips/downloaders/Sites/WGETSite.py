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

# Python Standard Libraries
import re
import shutil
import os
import logging
from subprocess import Popen,PIPE
from datetime import datetime
import requests



# GeoIPS Libraries
from .Site import Site
from geoips.utils.path.datafilename import DataFileName

log = logging.getLogger(__name__)


class WGETSite(Site):
    '''Class defining an http connection'''
    def __init__(self,host,downloadactive,**kwargs):
        super(WGETSite,self).__init__(host,downloadactive,**kwargs)

#    @retry((EOFError,socket.timeout))
    def login(self,timeout=''):
        log.info('Don\'t have to log into WGETSite. Just return True')

        return True

    def getLinksFromHTML(self,html,restring):
        files = []
        for line in html:
            if 'a href' in line:
                htmlobj = re.compile(
                    restring,
                    re.IGNORECASE)
                matchobj = htmlobj.match(line)
                try:
                    files.append(matchobj.group(1))
                except:
                    pass
        return files

    def wget_file(self,path,localfnstr):
        #rcj 13DEC2018 We're going to handle lance modis data downloads more pythonically
        #so this bit is only for lance modis data from the NASA Earth Data LANCE Near Real Time data server
        if hasattr(self,'host') and (self.host == 'nrt3.modaps.eosdis.nasa.gov' or self.host == 'nrt4.modaps.eosdis.nasa.gov'):
            headers = { 'Authorization': 'Bearer ' + self.appkey }
            try:
                r = requests.get('https://'+self.host+path,headers=headers)
                #if we get a good response, save the file to where geoips thinks it should go
                if r.status_code == 200:
                    log.info('After requesting modis data, the server responded with a status code of {0}.  Downloading the response object and writing to {1}'.format(r.status_code,localfnstr))
                    with open(localfnstr, 'wb') as downloadedFile:
                        downloadedFile.write(r.content)
                # if there is a non 200 response something has probably gone wrong
                elif r.status_code != 200:
                    log.info('There was a problem requesting the modis data.  The server responded with a status code of {0}.'.format(r.status_code))
                else:
                    log.info('There was a problem requesting the modis data.')
                    
            except Exception as e:
                log.info('There was a problem requesting the modis data: ',str(e))            
        else:
            if hasattr(self,'username'):
                wget_call = ['wget', path, '-4','--user='+self.username,'--password='+self.password,'--no-check-certificate','-O',localfnstr]
            else:
                wget_call = ['wget', path, '-4','--no-check-certificate','-O',localfnstr]
            log.info('****Running '+' '.join(wget_call))
            try:
                stdout, stderr = Popen(wget_call, stdout=PIPE, stderr=PIPE).communicate()
            except Exception as err:
                print('Error making request: ' + str(err))
            log.info(stdout)
            log.info(stderr)
        
        return localfnstr

    def getsinglefilelist(self,start_time,end_time,searchstring,login=True,subdir=None):

        if subdir is not None:
            fullurlpath=self.baseurl+'/'+subdir
        else:
            fullurlpath=self.baseurl

        log.info('')
        log.info('fullurlpath: '+str(fullurlpath)+'/'+str(searchstring))

    
        indexhtmlfile = DataFileName()
        indexhtmlfile.satname = 'wgetsite'
        indexhtmlfile.sensorname = self.data_type
        indexhtmlfile.dataprovider = self.host_type
        # Hmm, FileName object should probably set this when datetime is set?
        dt = datetime.utcnow()
        indexhtmlfile.time = dt.strftime(indexhtmlfile.datetime_fields['time'])
        indexhtmlfile.date = dt.strftime(indexhtmlfile.datetime_fields['date'])
        indexhtmlfile.extra = 'index'
        indexhtmlfile.ext = 'html'
        indexhtmlfile = indexhtmlfile.create_scratchfile()
        indexhtmlfile.makedirs()
        indexhtmlfnstr  = indexhtmlfile.name
        log.info(indexhtmlfnstr)

        # rcj 13DEC2018 this part doesn't need to run for lance modis data
        # it is handled in lance_modis.py getfilelist
        if hasattr(self,'host') and (self.host == 'nrt3.modaps.eosdis.nasa.gov' or self.host == 'nrt4.modaps.eosdis.nasa.gov'):
            pass
        #everything that is not lance modis that uses this script should still pass through here
        else:
            htmlfilelist = open(self.wget_file(fullurlpath,indexhtmlfnstr)).readlines()
            #getfiles = self.getLinksFromHTML(htmlfilelist,r'''.*a href="GAASP-MBT_v"."r"."GW"."_s[0-9]{14}".*''')
            #log.info(htmlfilelist)
            links = self.getLinksFromHTML(htmlfilelist,searchstring)
    
            # This is defined in Site.py - finding the files in the file list is 
            # common between HTTP and FTP (getting the lists differs, but sorting
            # through the list and returning the desired files is shared)
            return self.find_files_in_range(links,start_time,end_time,urlpath=fullurlpath)

#    @retry((socket.timeout,ftplib.error_temp,socket.error))
    def getfile(self,remotefile,localfile):
        processingfile = localfile+'.processing'
        ff = open(processingfile,'w')
        ff.close
        log.info('Touching temporary file: '+os.path.basename(processingfile))
        temp_filename = DataFileName(localfile).create_scratchfile()
        temp_filename.makedirs()
        temp_fnstr = temp_filename.name
        if not self.downloadactive:
            log.info('      *** nodownload set, not downloading remotefile %s ' % remotefile)
            log.info('      ***     to localfile %s' % localfile)
        else:
            log.info('      *** grabbing remotefile %s ' % remotefile)
            log.info('      ***     to localfile %s' % localfile)
            self.wget_file(remotefile,temp_fnstr)

        self.move_to_final(temp_fnstr,processingfile,localfile)
