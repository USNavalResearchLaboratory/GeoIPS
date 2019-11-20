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
import shutil
import logging
import httplib
import ssl
import urllib2
import socket
import re


# GeoIPS Libraries
from .Site import Site
from geoips.utils.decorators import retry,timeout,TimeoutError
from geoips.utils.path.path import Path

log=logging.getLogger(__name__)

class TLS1Connection(httplib.HTTPSConnection):
    """Like HTTPSConnection but more specific"""
    def __init__(self, host, **kwargs):
        httplib.HTTPSConnection.__init__(self, host, **kwargs)

    def connect(self):
        """Overrides HTTPSConnection.connect to specify TLS version"""
        # Standard implementation from HTTPSConnection, which is not
        # designed for extension, unfortunately
        sock = socket.create_connection((self.host, self.port),
            self.timeout, self.source_address)
        if getattr(self, '_tunnel_host', None):
            self.sock = sock
            self._tunnel()

        # This is the only difference; default wrap_socket uses SSLv23
        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
            ssl_version=ssl.PROTOCOL_TLSv1)

class TLS1Handler(urllib2.HTTPSHandler):
    """Like HTTPSHandler but more specific"""
    def __init__(self):
        urllib2.HTTPSHandler.__init__(self)

    def https_open(self, req):
        return self.do_open(TLS1Connection, req)


class HTTPSite(Site):
    '''Class defining an http connection'''
    def __init__(self,host,downloadactive=True,**kwargs):
        super(HTTPSite,self).__init__(host,downloadactive,**kwargs)

#    @retry((EOFError,socket.timeout))
    def login(self,timeout=''):
        try:
            log.info('Trying to open '+self.baseurl)
            handle=urllib2.urlopen(self.baseurl)
            log.info('Successfully opened '+self.baseurl)
        except IOError,e:
            if 'Connection timed out' in str(e):
                log.error(str(e)+' Connection timed out, try again later')
                raise TimeoutError(str(e)+' Connection timed out, try again later')
            if "EOF occurred in violation of protocol" in str(e):
                log.info(str(e)+' Now trying to open with TLS1.2')
                opener = urllib2.build_opener(TLS1Handler())
            else:
                log.info(str(e)+' Now trying to open with Authorization')
                authline = e.headers['www-authenticate']
                log.info(authline)
                (scheme,realm) = self.getSchemeAndRealm(authline)
                log.info('    realm is '+realm)
                log.info('    scheme is "'+scheme+'"')
                if scheme == 'Basic':
                    log.info(' Running basic')
                    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                    password_mgr.add_password(realm,self.baseurl,self.username,self.password)
                    handler = urllib2.HTTPBasicAuthHandler(password_mgr)
                    opener = urllib2.build_opener(handler)
                else:
                    log.info(' Running digest')
                    password_mgr = urllib2.HTTPPasswordMgr()
                    password_mgr.add_password(realm,self.baseurl,self.username,self.password)
                    handler = urllib2.HTTPDigestAuthHandler(password_mgr)
                    opener = urllib2.build_opener(handler)
            log.info(' Installing opener')
            urllib2.install_opener(opener)

        return True

    def getSchemeAndRealm(self,authline):
        authobj = re.compile(
            r'''(?:\s*www-authenticate\s*:)?\s*(\w*)\s+realm=['"]([^'"]+)['"]''',
            re.IGNORECASE)
        # this regular expression is used to extract scheme and realm
        matchobj = authobj.match(authline)

        if not matchobj:
            # if the authline isn't matched by the regular expression
            # then something is wrong
            print 'The authentication header is badly formed.'
            print authline
            #sys.exit(1)
            raise

        scheme = matchobj.group(1)
        realm = matchobj.group(2)
        return (scheme,realm)

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

    @timeout(600)
    def writefile(self,local_file,remote_file):
        open(local_file,'wb').write(urllib2.urlopen(remote_file).read())

    @retry((socket.timeout,urllib2.URLError))
    def getsinglefilelist(self,start_time,end_time,searchstring,login=True,subdir=None):

        if login == True:
            log.info('Logging into '+self.baseurl)
            self.login()
            log.info('Done logging into '+self.baseurl)

        if subdir is not None:
            fullurlpath=self.baseurl+'/'+subdir
        else:
            fullurlpath=self.baseurl

        log.info('')
        log.info('fullurlpath: '+str(fullurlpath)+'/'+str(searchstring))

        try:
            htmlfilelist = urllib2.urlopen(fullurlpath,None,5).readlines()
        except (socket.timeout),resp:
            log.warning(str(resp)+'Timed out trying to open '+self.baseurl)
            raise
        except (urllib2.URLError),resp:
            log.warning(str(resp)+' Failed getting html file list')
            self.login()
            raise
        links = self.getLinksFromHTML(htmlfilelist,searchstring)

        # This is defined in Site.py - finding the files in the file list is
        # common between HTTP and FTP (getting the lists differs, but sorting
        # through the list and returning the desired files is shared)
        return self.find_files_in_range(links,start_time,end_time,urlpath=fullurlpath)

    def getfile(self,remotefile,localfile):
        processingfile = localfile+'.processing'
        ff = open(processingfile,'w')
        ff.close
        log.info('Touching temporary file: '+os.path.basename(processingfile))
        temp_filename = Path(os.getenv('SCRATCH')+'/'+os.path.basename(processingfile)+str(os.getpid()))
        temp_filename.makedirs()
        temp_file = temp_filename.name
        if not self.downloadactive:
            log.info('      *** nodownload set, not downloading remotefile %s ' % remotefile)
            log.info('      ***     to localfile %s' % localfile)
        else:
            log.info('      *** grabbing remotefile %s ' % remotefile)
            log.info('      ***     to localfile %s' % localfile)
            try:
                self.writefile(temp_file,remotefile)
            except TimeoutError,resp:
                log.warning(str(resp)+': urllib2.urlopen timed out, deleting temporary file and trying again next time')
                os.unlink(temp_file)
                os.unlink(processingfile)
                raise
        self.move_to_final(temp_file,processingfile,localfile)
