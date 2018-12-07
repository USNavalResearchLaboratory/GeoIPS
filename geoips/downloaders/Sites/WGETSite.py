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
        if hasattr(self,'username'):
            #rcj 07DEC2018 this is a special case for the update to api used in lance_modis.py. The api changed in 2018 to require an appkey.  
            #If there are many more 'special cases' then the whole scheme of routing ftp/http request handling through here may need to be re-assessed
            if hasattr(self,'appkey'):
                wget_call = ['wget', '-e robots=off -m -np -R .html,.tmp -nH --cut-dirs=4', path, '--header "Authorization: Bearer '+self.appkey+'"', '-P' ,localfnstr]
            else:
                wget_call = ['wget', path, '-4','--user='+self.username,'--password='+self.password,'--no-check-certificate','-O',localfnstr]
        else:
            wget_call = ['wget', path, '-4','--no-check-certificate','-O',localfnstr]
        log.info('****Running '+' '.join(wget_call))
        stdout, stderr = Popen(wget_call, stdout=PIPE, stderr=PIPE).communicate() 
        #log.debug(stdout)
        #log.info(stderr)
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
