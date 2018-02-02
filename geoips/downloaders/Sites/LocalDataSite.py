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
import logging
import shutil
import os


# GeoIPS Libraries
from .Site import Site


log=logging.getLogger(__name__)


class LocalDataSite(Site):
    '''Class defining a file mover (data that was already pushed to us locally)'''
    max_connections = 7
    def __init__(self,downloadactive=True,**kwargs):
        if not hasattr(self,'host') or not self.host:
            self.host = 'localdir'
        self.run_geoips = False
        #self.host_type = 'viirsberylrdr'
        super(LocalDataSite,self).__init__(self.host,downloadactive,**kwargs)

    def getfile(self,remotefile,localfile):
        processingfile = localfile+'.processing'
        ff = open(processingfile,'w')
        ff.close
        log.info('Touching temporary file: '+os.path.basename(processingfile))
        if not self.downloadactive:
            log.info('      *** nodownload set, not moving pushed file %s ' % remotefile)
            log.info('      ***     to localfile %s' % localfile)
        else:
            log.info('      *** moving pushed file %s ' % remotefile)
            log.info('      ***     to localfile %s' % localfile)

        self.move_to_final(remotefile,processingfile,localfile)


