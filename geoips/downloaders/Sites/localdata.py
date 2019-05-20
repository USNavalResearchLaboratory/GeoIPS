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
import logging
from glob import glob
import shutil
import os
from datetime import datetime,timedelta
import hashlib


# Installed Libraries
from IPython import embed as shell


# GeoIPS Libraries
from .LocalDataSite import LocalDataSite
from geoips.utils.path.datafilename import DataFileName
from geoips.utils.satellite_info import SatSensorInfo


log = logging.getLogger(__name__)

class TESTLOCAL_TESTABI_LOCALDATA(LocalDataSite):
    ''' Subclass of LocalDataSite for initiating processing of
            locally available ABI data.

        Data_type and host_type are used as keys for running downloader
            ./downloaders/downloader.py abi local
        host is only used for display purposes for LocalDataSite -
            set to the actual remote site for FTP/HTTP. '''
    data_type = 'testabi'
    host_type = 'testlocal'
    host = 'localdirs '

    # List the base_dirs that are set in utils/satellite_info.py
    # These will show up  for logging purposes when you run
    #   ./downloaders/downloader.py
    sensor_info = SatSensorInfo('goes16','abi')
    for currdir in sensor_info.OrigFNames:
        if 'base_dir' in currdir.keys() and currdir['base_dir']:
            host += ' '+currdir['base_dir']

    def __init__(self,downloadactive=True,bandlist=None,**kwargs):
        ''' Required __init__ method, set up downloader attributes:
                queue parameters
                    * queue set to $DEFAULT_QUEUE by default in downloader.py
                    *       (None if DEFAULT_QUEUE not set)
                    * can set the num cpus and mem per cpu here.
                GeoIPS processing parameters
                    * self.run_geoips defaults to False!
                External processing scripts
                    * self.pp_script : if defined, will run non-GeoIPS processing'''

        super(TESTLOCAL_TESTABI_LOCALDATA,self).__init__(downloadactive,bandlist=bandlist,**kwargs)
        self.run_geoips = True
        self.mp_max_cpus = 8
        self.mp_mem_per_cpu = 25
        #self.pp_script = os.getenv('PROCSDIR')+'/h8/h8_postprocs'

    def get_final_filename(self,file):
        ''' Keep original filename, but use standard path
            The default for this method uses GeoIPS standard
            filename and GeoIPS standard path. '''
        fn = DataFileName(os.path.basename(file))
        sdfn = fn.create_standard(downloadSiteObj=self)
        return os.path.dirname(sdfn.name)+'/'+os.path.basename(file)


    def sort_files(self,filelist):
        # OR_ABI-L1b-RadF-M3C02_G16_s20170642036100_e20170642046467_c20170642046500.nc
        # OR_ABI-L1b-RadC-M3C03_G16_s20171070042189_e20171070044562_c20171070045005.nc
        # OR_SEIS-L1b-EHIS_G16_s20170622315250_e20170622315250_c20170622320253.nc
        # DataFileName way too slow, need to fix that. For now, just 
        # sort directly
        filelist.sort(cmp,key=lambda x:os.path.basename(x).split('_')[3],reverse=True)
        return filelist


    def getfile(self,remotefile,localfile):
        log.info('Just creating symlink from original '+remotefile+' to final '+localfile)
        if not self.downloadactive:
            log.info('      *** nodownload set, not moving pushed file %s ' % remotefile)
            log.info('      ***     to localfile %s' % localfile)
        else:
            log.info('      *** moving pushed file %s ' % remotefile)
            log.info('      ***     to localfile %s' % localfile)
            os.symlink(remotefile,localfile)

    def run_on_files(self,final_file):
        ''' The default for this method runs on every file that 
            is downloaded.  Overriding for ABI to only process when
            a directory contains 16 files. Also allow for limiting
            the frequency we actually try to process if we can't
            keep up '''

        runtype = 'RadF'

        dirname = os.path.dirname(final_file)
        # List all RadF files
        listthesefiles = dirname+'/*{0}*'.format(runtype)

        files = glob(listthesefiles)
        num_files = len(files)
        log.info('  In run_on_files TESTLOCAL_TESTABI '+str(num_files)+' files in directory '+listthesefiles)

        # Limit frequency we actually process 
        dfn = DataFileName(os.path.basename(final_file)).create_standard()
        if dfn.datetime.minute != 0 and dfn.datetime.minute != 30: 
            log.info('ONLY RUNNING 0 30 MINUTES FOR NOW. Skipping processing')
            return []

        # Once we get 16 files, and the current file is RadF, kick off processing 
        if num_files == 16 and runtype in final_file:
            return [final_file]
        else:
            return []

    def getfilelist(self,start_datetime,end_datetime):

        # Data locations are specified in $GEOIPS/utils/satellite_info.py
        # and $GEOIPS/utils/path/datafilename.py 

        files = []
        for dir in self.sensor_info.OrigFNames:
            if 'base_dir' in dir.keys() and dir['base_dir']:
                # Files go in base_dir/YYYYMMDD/OR_*.nc 
                # where basedir is $BIGDATA/incoming
                log.info('    Finding appropriate files in '+dir['base_dir']+'/*/OR_*.nc ...')
                currfiles = glob(dir['base_dir']+'/*/OR_*.nc')
                files += currfiles
        return files
