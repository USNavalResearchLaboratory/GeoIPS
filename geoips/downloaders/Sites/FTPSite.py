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
import os
import fnmatch
import ftplib
import socket
import logging
import shutil


# Installed Libraries 
try:
    import paramiko
except:
    print 'Failed paramiko import in FTPSite.py. If you need it, install it.'


# GeoIPS Libraries
from .Site import Site
from geoips.utils.decorators import timeout,TimeoutError,retry
from geoips.utils.path.path import Path


log=logging.getLogger(__name__)

@timeout(3)
def auth_publickey(transport,username,key):
    transport.auth_publickey(username=username,key=key)

class FTPSite(Site):
    '''Class defining an ftp connection'''
    def __init__(self,host,downloadactive=True,**kwargs):
        super(FTPSite,self).__init__(host,downloadactive,**kwargs)

    @retry((ftplib.error_perm,EOFError,socket.timeout))
    def login(self,timeout=''):
        try:
            if hasattr(self,'sftp'):
                transport = paramiko.Transport((self.host,22))
                if hasattr(self,'password'):
                    transport.connect(username=self.username,password=self.password)
                elif hasattr(self,'pkey'):
                    key = paramiko.DSSKey.from_private_key_file(self.pkey)
                    transport.start_client(event=None)
                    transport.get_remote_server_key()
                    try:
                        auth_publickey(transport,username=self.username,key=key)
                    except TimeoutError,resp:
                        log.exception('Timed out trying to authorize public key:'+str(resp))
                        return False

                f = paramiko.SFTPClient.from_transport(transport)
            else:
                if timeout:
                    f = ftplib.FTP(self.host,timeout=timeout)
                else:
                    f = ftplib.FTP(self.host)
        #except (socket.error, socket.gaierror), e: 
        except (EOFError,socket.timeout): 
            log.exception('      *** ERROR: cannot reach "%s"' % self.host)
            raise
        except ftplib.error_reply,resp:
            log.warning(str(resp)+': dont raise this, just an info message... trying again')
        log.info('      *** Connected to host "%s"' % self.host)

        if not hasattr(self,'sftp'):
            try: 
                f.login(self.username,self.password)
                log.info('      *** Logged in as username %s' % self.username)
            except (ftplib.error_perm,EOFError,socket.timeout,socket.error),resp:
                log.error('      *** ERROR: cannot login'+str(resp))
                f.quit()
                raise
            except ftplib.error_reply,resp:
                log.warning(str(resp)+': dont raise this, just an info message... trying again')

            f.set_pasv(True)
        self.con = f
        return f

    @retry(Exception)
    def getsinglefilelist(self,subdir,match_string,start_time,end_time,ignore_strings=[]):

        # Should not ever need space / at the beginning or end of subdir (and / at end breaks the os.path.dirname part - 
        # it does not match so tries to prepend subdir unecessarily, nothing works)
        # Changed the strip to rstrip to remove only the ending slash.  Sometimes subdir
        # is the full path as example for bft.
        subdir = subdir.strip()
        subdir = subdir.rstrip('/')

        log.info('Matching files: '+self.host+'/'+subdir+'/'+match_string+' Ignoring strings: '+str(ignore_strings))

        if not hasattr(self,'sftp'):
            #log.info('Regular FTP list')
            try:
                tfls = self.con.nlst(subdir+'/'+match_string)
            except ftplib.error_perm,resp:
                if '550 No such file or directory' in str(resp):
                    log.warning(str(resp))
                    return []
                else:
                    log.exception(str(resp))
                    raise
            except ftplib.error_temp,resp:
                if '450 No files found' in str(resp):
                    log.warning(str(resp))
                    return []
                else:
                    log.exception(str(resp))
                    raise
            except socket.timeout,resp:
                log.warning(str(resp)+': nlst timed out, trying again: '+subdir)
                raise
            except socket.error,resp:
                log.warning(str(resp)+': nlst had socket.error, trying again')
                log.warning('        Resetting connection')
                try:
                    self.con.quit()
                except (ftplib.error_temp),resp:
                    log.warning(str(resp)+':  Failed closing the connection with ftplib.error_temp... Lets just ignore that')      
                except (socket.error),resp:
                    log.warning(str(resp)+':  Failed closing the connection with socket.error... Lets just ignore that')      
                self.con = self.login(timeout=20)
                raise
        else:
            #log.info('SFTP list')
            tfls = fnmatch.filter(self.con.listdir(subdir),match_string)


        # FTP list sometimes returns just filename, sometimes subdir+'/'+filename ...
        # handle both
        fls = [ff if subdir in os.path.dirname(ff) else subdir+'/'+ff for ff in tfls]

        for ignore_string in ignore_strings:
            fls = [ff for ff in fls if ignore_string not in ff ]

        # This is defined in Site.py - finding the files in the file list is 
        # common between HTTP and FTP (getting the lists differs, but sorting
        # through the list and returning the desired files is shared)
        return self.find_files_in_range(fls,start_time,end_time)

    @retry((socket.timeout,ftplib.error_temp,ftplib.error_perm,ftplib.error_reply,socket.error,EOFError,AttributeError))
    def getfile(self,remotefile,localfile):
        if not hasattr(self,'con') or not self.con:
            if not hasattr(self,'con'):
                log.info('Connection not set! Logging in...')
            else:
                log.info('Connection is None! Logging in again...')
            self.con = self.login(timeout=20)

        processingfilename = Path(localfile+'.processing')
        processingfilename.makedirs()
        processingfile = processingfilename.name
        ff = open(processingfile,'w')
        ff.close
        log.info('Touching temporary file: '+os.path.basename(processingfile))
        temp_filename = Path(os.getenv('SCRATCH')+'/'+os.path.basename(processingfile)+str(os.getpid()))
        temp_filename.makedirs()
        temp_file = temp_filename.name
        if not self.downloadactive:
            log.info('      *** noftp set, not ftping remotefile %s ' % remotefile)
            log.info('      ***     to localfile %s' % localfile)
        else:
            log.info('      *** ftping remotefile %s ' % remotefile)
            log.info('      ***     to localfile %s' % localfile)
            if hasattr(self,'sftp'):
                self.con.get(remotefile,temp_file)
            else:
                try:
                    self.con.retrbinary('RETR '+remotefile,open(temp_file, 'wb').write)
                except socket.timeout,resp:
                    log.warning(str(resp)+': RETR timed out on '+remotefile+' trying again')
                    try:
                        os.unlink(processingfile)
                    except OSError,resp:
                        log.warning(str(resp)+': Failed deleting processing file. Ignore, someone else probably did it for us.')
                    log.warning('        Resetting connection')
                    try:
                        self.con.quit()
                    except (ftplib.error_temp),resp:
                        log.warning(str(resp)+':  Failed closing the connection with ftplib.error_temp... Lets just ignore that')      
                    except (socket.error),resp:
                        log.warning(str(resp)+':  Failed closing the connection with socket.error... Lets just ignore that')      
                    self.con = self.login(timeout=20)
                    raise
                except socket.error,resp:
                    log.warning(str(resp)+': RETR had socket.error on '+remotefile+' trying again')
                    try:
                        os.unlink(processingfile)
                    except OSError,resp:
                        log.warning(str(resp)+': Failed deleting processing file. Ignore, someone else probably did it for us.')
                    log.warning('        Resetting connection')
                    try:
                        self.con.quit()
                    except (ftplib.error_temp),resp:
                        log.warning(str(resp)+':  Failed closing the connection with ftplib.error_temp... Lets just ignore that')      
                    except (socket.error),resp:
                        log.warning(str(resp)+':  Failed closing the connection with socket.error... Lets just ignore that')      
                    self.con = self.login(timeout=20)
                    raise
                except ftplib.error_temp,resp:
                    log.warning(str(resp)+': RETR failed error_temp '+remotefile+' trying again')
                    try:
                        os.unlink(processingfile)
                    except OSError,resp:
                        log.warning(str(resp)+': Failed deleting processing file. Ignore, someone else probably did it for us.')
                    log.warning('        Resetting connection')
                    try:
                        self.con.quit()
                    except (ftplib.error_temp),resp:
                        log.warning(str(resp)+':  Failed closing the connection with ftplib.error_temp... Lets just ignore that')      
                    except (socket.error),resp:
                        log.warning(str(resp)+':  Failed closing the connection with socket.error... Lets just ignore that')      
                    self.con = self.login(timeout=20)
                    raise
                except ftplib.error_perm,resp:
                    log.warning(str(resp)+': RETR failed error_perm '+remotefile+' trying again')
                    try:
                        os.unlink(processingfile)
                    except OSError,resp:
                        log.warning(str(resp)+': Failed deleting processing file. Ignore, someone else probably did it for us.')
                    log.warning('        Resetting connection')
                    try:
                        self.con.quit()
                    except (ftplib.error_temp),resp:
                        log.warning(str(resp)+':  Failed closing the connection with ftplib.error_temp... Lets just ignore that')      
                    except (socket.error),resp:
                        log.warning(str(resp)+':  Failed closing the connection with socket.error... Lets just ignore that')      
                    self.con = self.login(timeout=20)
                    raise
                except ftplib.error_reply,resp:
                    log.warning(str(resp)+': just an info message, but we still need to download... '+remotefile+' trying again')
                    try:
                        os.unlink(processingfile)
                    except OSError,resp:
                        log.warning(str(resp)+': Failed deleting processing file. Ignore, someone else probably did it for us.')
                    raise
                except EOFError,resp:
                    log.warning(str(resp)+': RETR failed EOFError '+remotefile+' trying again')
                    try:
                        os.unlink(processingfile)
                    except OSError,resp:
                        log.warning(str(resp)+': Failed deleting processing file. Ignore, someone else probably did it for us.')
                    log.warning('        Resetting connection')
                    try:
                        self.con.quit()
                    except (ftplib.error_temp),resp:
                        log.warning(str(resp)+':  Failed closing the connection with ftplib.error_temp... Lets just ignore that')      
                    except (socket.error),resp:
                        log.warning(str(resp)+':  Failed closing the connection with socket.error... Lets just ignore that')      
                    self.con = self.login(timeout=20)
                    raise
                except AttributeError,resp:
                    log.warning(str(resp)+': RETR failed AttributeError '+remotefile+' trying again')
                    try:
                        os.unlink(processingfile)
                    except OSError,resp:
                        log.warning(str(resp)+': Failed deleting processing file. Ignore, someone else probably did it for us.')
                    log.warning('        Resetting connection')
                    try:
                        self.con.quit()
                    except (ftplib.error_temp),resp:
                        log.warning(str(resp)+':  Failed closing the connection with ftplib.error_temp... Lets just ignore that')      
                    except (socket.error),resp:
                        log.warning(str(resp)+':  Failed closing the connection with socket.error... Lets just ignore that')      
                    except (AttributeError),resp:
                        log.warning(str(resp)+':  Failed closing the connection with AttributeError... Lets just ignore that')      
                    self.con = self.login(timeout=20)
                    raise

            self.move_to_final(temp_file,processingfile,localfile)

