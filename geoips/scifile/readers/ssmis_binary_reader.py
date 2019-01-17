# Python Standard Libraries
import logging
import os
from datetime import datetime
from subprocess import Popen, PIPE
from operator import mul
from math import floor, ceil
import sys
import string


# Installed Libraries
from IPython import embed as shell
# If this reader is not installed on the system, don't fail altogether, just skip this import. This reader will
# not work if the import fails, and the package will have to be installed to process data of this type.
try: import pygrib as pg
except: print 'Failed import netCDF4 in scifile/readers/amsr2_ncdf4_reader.py. If you need it, install it.'
import numpy as np


# GeoIPS Libraries
from .reader import Reader
from ..containers import _empty_varinfo
from geoips.utils.path.datafilename import DataFileName
from geoips.utils.satellite_info import SatSensorInfo

log = logging.getLogger(__name__)






# For now must include this string for automated importing of classes.
reader_class_name = 'SSMIS_BINARY_Reader'
class SSMIS_BINARY_Reader(Reader):

    dataset_info = { 'IMAGER': {'ch08':'ch08',
                              'ch09':'ch09',
                              'ch10':'ch10',
                              'ch11':'ch11',
                              'ch17':'ch17',
                              'ch18':'ch18',
                              'surface':'surface',
                              'rain':'rain',
                            },
                     'ENVIROEVEN': {'ch12e':'ch12e',
                              'ch13e':'ch13e',
                              'ch14e':'ch14e',
                              'ch15e':'ch15e',
                              'ch16e':'ch16e',
                              #'sea_ice':'sea_ice',
                              #'surface':'surface',
                            },
                     'ENVIROODD': {'ch12':'ch12',
                              'ch13':'ch13',
                              'ch14':'ch14',
                              'ch15':'ch15',
                              'ch16':'ch16',
                              'ch15_5x5':'ch15_5x5',
                              'ch16_5x5':'ch16_5x5',
                              'ch17_5x5':'ch17_5x5',
                              'ch18_5x5o':'ch18_5x5o',
                              'ch17_5x4':'ch17_5x4',
                              'ch18_5x4':'ch18_5x4',
                              #'sea_ice':'sea_ice',
                              #'surface':'surface',
                              #'rain1':'rain1',
                              #'rain2':'rain2',
                            },
                     'LAS': {'ch01_3x3':'ch01_3x3',
                              'ch02_3x3':'ch02_3x3',
                              'ch03_3x3':'ch03_3x3',
                              'ch04_3x3':'ch04_3x3',
                              'ch05_3x3':'ch05_3x3',
                              'ch06_3x3':'ch06_3x3',
                              'ch07_3x3':'ch07_3x3',
                              'ch08_5x5':'ch08_5x5',
                              'ch09_5x5':'ch09_5x5',
                              'ch10_5x5':'ch10_5x5',
                              'ch11_5x5':'ch11_5x5',
                              'ch18_5x5':'ch18_5x5',
                              'ch24_3x3':'ch24_3x3',
                              'height_1000mb':'height_1000mb',
                              'surf':'surf',
                            },
                     'UAS': {'ch19_6x6':'ch19_6x6',
                              'ch20_6x6':'ch20_6x6',
                              'ch21_6x6':'ch21_6x6',
                              'ch22_6x6':'ch22_6x6',
                              'ch23_6x6':'ch23_6x6',
                              'ch24_6x6':'ch24_6x6',
                              'scene':'scene',
                              'uas_tqflag':'uas_tqflag',
                            },
                   }
    gvar_info = { 'IMAGER': {
                         'Latitude': 'latitude',
                         'Longitude': 'longitude',
                        },
                  'ENVIROEVEN': {
                         'Latitude': 'latitude',
                         'Longitude': 'longitude',
                        },
                  'ENVIROODD': {
                         'Latitude': 'latitude',
                         'Longitude': 'longitude',
                        },
                  'LAS': {
                         'Latitude': 'latitude',
                         'Longitude': 'longitude',
                        },
                  'UAS': {
                         'Latitude': 'latitude',
                         'Longitude': 'longitude',
                        },
                }

    @staticmethod
    def format_test(fname):
        # This reader only handles individual files, not multiple files or directories.
        # Change def read and def format_test if you want to handle directories directly.
        if os.path.isdir(fname):
            return False

        # Check that this file is grib first
        from ..file_format_tests import bin_format_test
        if not bin_format_test(fname):
            return False

        #if 'US058SORB-RAW' not in fname:
        #    return False

        #Calling in the individual bytes to check the header
        f1 = open(fname,'rb')
        # short sw_rev, 1 int16
        sw_rev = np.fromstring(f1.read(2),dtype=np.dtype('short')).byteswap()[0]
        # char endian and file id, 1 byte each
        endian,fileid = np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
        # int rev and year, 4 bytes each
        rev = np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
        year = np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
        # short jday as 1 byte each
        jday = np.fromstring(f1.read(2),dtype=np.dtype('short')).byteswap()
        # char hour and minute as 1 byte each
        hour,minu = np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
        satid,nsdr = np.fromstring(f1.read(4),dtype=np.dtype('short')).byteswap()
        spare1,spare2,spare3= np.fromstring(f1.read(3),dtype=np.dtype('int8')).byteswap()
        proc_stat_flags = np.fromstring(f1.read(1),dtype=np.dtype('int8')).byteswap()
        spare4= np.fromstring(f1.read(2),dtype=np.dtype('short')).byteswap()
        #shell()

        if year > 1900 and year <4000 and \
           jday >=1 and jday <=366 and \
           hour >=0 and hour <=25 and \
           minu >=0 and minu <=59:
            return True
        return False


    def read(self,fname,datavars,gvars,metadata,chans=None,sector_definition=None):
        # Since the variables are all contained within separate files, we need to allow for 
        # a loop to cycle through the files

        #print 'Entering IPython shell in '+self.name+' for development purposes'
        #shell()
        f1 = open(fname,'rb')
        #READ HEARDER
        # short (short) sw_rev, 1 int16
        sw_rev = np.fromstring(f1.read(2),dtype=np.dtype('short')).byteswap()[0]
        # char (int8) endian and fileid, 1 byte each
        endian,fileid = np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
        # int (int32) rev and year as 2 bytes each
        rev = np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
        year = np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
        #rev = int(float(rev))
        #year = int(float(year))
        jday = np.fromstring(f1.read(2),dtype=np.dtype('short')).byteswap()
        hour,minu = np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
        satid,nsdr = np.fromstring(f1.read(4),dtype=np.dtype('short')).byteswap()
        spare1,spare2,spare3= np.fromstring(f1.read(3),dtype=np.dtype('int8')).byteswap()
        proc_stat_flags = np.fromstring(f1.read(1),dtype=np.dtype('int8')).byteswap()
        spare4= np.fromstring(f1.read(2),dtype=np.dtype('short')).byteswap()
        #Need to set up time to be read in by the metadata (year and jday are arrays)
        time= '%04d%03d%02d%02d' % (year[0],jday[0],hour,minu)
        #Read in the number of bytes being read in by the header
        nbytes=26 #bytes that have been read in
        #Read scan records at 512-byte boundaries
        nfiller= 512-( nbytes % 512 )
        filler_bytes= np.fromstring(f1.read(nfiller),dtype=np.dtype('int8')).byteswap()[0]
        if satid == 1:
            satid= 'f16'
        elif satid==2:
            satid= 'f17'
        elif satid==3:
            satid= 'f18'
        elif satid==4:
            satid= 'f19'
        else:
            return False
        #shell()
        #Enter metadata
        metadata['top']['start_datetime'] = datetime.strptime(time,'%Y%j%H%M')
        metadata['top']['end_datetime'] = datetime.strptime(time,'%Y%j%H%M')
        metadata['top']['dataprovider'] = 'DMSP'
        metadata['top']['filename_datetime'] = metadata['top']['start_datetime']
        metadata['top']['platform_name'] = satid
        metadata['top']['source_name'] = 'ssmis'
        si = SatSensorInfo(metadata['top']['platform_name'],metadata['top']['source_name'])
        if not si:
            raise SciFileError('Unrecognized platform and source name combination: '+metadata['top']['platform_name']+' '+metadata['top']['source_name'])

        dfn = DataFileName(os.path.basename(fname))
        if dfn:
            sdfn = dfn.create_standard()
            metadata['top']['filename_datetime'] = sdfn.datetime

        # Tells driver to NOT try to sector this data.
        metadata['top']['NON_SECTORABLE'] = True

        if chans == []:
            return

        #Need to create a loop for the nbytes, the C code is:
        #for(n= 0; n< rev.nsdr; n++){
        #    nsdr++;
        #    nbytes= 0;
        bad_value= -999
        tarray= np.zeros(nsdr*28)
        iarray= np.zeros(180*nsdr*28)
        bufch08= np.ma.masked_equal(iarray,bad_value)
        #for a in range(nsdr*28*180):
            #bufch08[a]=bad_value
        bufdate= np.ma.masked_equal(tarray,bad_value)
        buftime= np.ma.masked_equal(tarray,bad_value)
        ttime=[]
        tdate=[]
        for nn in range(nsdr):
            log.info('    Reading sdr #'+str(nn)+' of '+str(nsdr))
            nbytes=0

        #SCAN HEADER
            syncword= np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
            scan_year= np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
            scan_jday= np.fromstring(f1.read(2),dtype=np.dtype('short')).byteswap()
            scan_hour,scan_minu= np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
            scan= np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
            nscan_imager, nscan_enviro, nscan_las, nscan_uas= np.fromstring(f1.read(4),dtype=np.dtype('int8')).byteswap()
            start_scantime_imager= np.fromstring(f1.read(112),dtype=np.dtype('int32')).byteswap()
            scenecounts_imager= np.fromstring(f1.read(28),dtype=np.dtype('uint8')).byteswap()
            start_scantime_enviro= np.fromstring(f1.read(96),dtype=np.dtype('int32')).byteswap()
            scenecounts_enviro= np.fromstring(f1.read(24),dtype=np.dtype('uint8')).byteswap()
            start_scantime_las= np.fromstring(f1.read(32),dtype=np.dtype('int32')).byteswap()
            scenecounts_las= np.fromstring(f1.read(8),dtype=np.dtype('uint8')).byteswap()
            start_scantime_uas= np.fromstring(f1.read(16),dtype=np.dtype('int32')).byteswap()
            scenecounts_uas= np.fromstring(f1.read(4),dtype=np.dtype('uint8')).byteswap()
            spare= np.fromstring(f1.read(20),dtype=np.dtype('int32')).byteswap()
            nbytes+= 360
            nscan0 = scan - 1
            #shell()
#-----------------------------------------------------------------------------------------
            try:
                imager_read= np.ma.zeros((nscan_imager,180))
                np.ma.masked_all_like(imager_read)
                #imager_read= np.ma.masked_all((nscan_imager,scenecounts_imager[0]))
                #imager_read.fill(-999)
            except:
                print 'Shell dropped for imager_read'
                #shell()
            if scenecounts_imager[0] < 0 or scan_year != 2017:
                print "IMAGER is negative"
                #shell()
            #imager_read= np.ma.zeros((nscan_imager,scenecounts_imager[0]))
            lt = np.ma.masked_values(imager_read,bad_value)
            lg = np.ma.masked_values(imager_read,bad_value)
            ch08 = np.ma.masked_values(imager_read,bad_value)
            ch09 = np.ma.masked_values(imager_read,bad_value)
            ch10 = np.ma.masked_values(imager_read,bad_value)
            ch11 = np.ma.masked_values(imager_read,bad_value)
            ch17 = np.ma.masked_values(imager_read,bad_value)
            ch18 = np.ma.masked_values(imager_read,bad_value)
            surf = np.ma.masked_values(imager_read,bad_value)
            rain = np.ma.masked_values(imager_read,bad_value)
            #shell()
            #IMAGER READ DATA
            for ii in range(nscan_imager):
                if start_scantime_imager[ii] == -999:
                    print 'value of imager scan is %d'% ii
                    continue
                #if start_scantime_imager[ii] >=0 and start_scantime_imager[ii] <= 86400000:
                #    itime= '%04d%03d' % (scan_year[0],scan_jday[0])
                #    tdate= datetime.strptime(itime,'%Y%j')
                #    ttime= 0.001*start_scantime_imager[ii]
                #    k= int(nscan0+ii)
                #    #shell()
                #    bufdate[k]=itime
                #    buftime[k]=ttime
                for jj in range(scenecounts_imager[ii]):
                    imager_lat, imager_lon, imager_scene= np.fromstring(f1.read(6),dtype=np.dtype('short')).byteswap()
                    imager_surf, imager_rain= np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
                    imager_ch08,imager_ch09,imager_ch10,imager_ch11,imager_ch17,imager_ch18= np.fromstring(f1.read(12),dtype=np.dtype('short')).byteswap()
                    nbytes+= 20
                    k= 180*(nscan0+ii)+jj
                    lat= 0.01*imager_lat
                    lon= 0.01*imager_lon
                    #bufch08[k]= imager_ch08
                    try:
                        lt[ii][jj] = lat
                        lg[ii][jj] = lon
                        ch08[ii][jj] = imager_ch08
                        ch09[ii][jj] = imager_ch09
                        ch10[ii][jj] = imager_ch10
                        ch11[ii][jj] = imager_ch11
                        ch17[ii][jj] = imager_ch17
                        ch18[ii][jj] = imager_ch18
                        surf[ii][jj] = imager_surf
                        rain[ii][jj] = imager_rain
                    except:
                        print 'Failed setting arrays in scan_imager'
                        #shell()
            if 'Latitude' not in gvars['IMAGER'].keys():
                    gvars['IMAGER']['Latitude']=lt
                    gvars['IMAGER']['Longitude']=lg
                    datavars['IMAGER']['ch08']=ch08
                    datavars['IMAGER']['ch09']=ch09
                    datavars['IMAGER']['ch10']=ch10
                    datavars['IMAGER']['ch11']=ch11
                    datavars['IMAGER']['ch17']=ch17
                    datavars['IMAGER']['ch18']=ch18
                    datavars['IMAGER']['surface']=surf
                    datavars['IMAGER']['rain']=rain
            else:
                    gvars['IMAGER']['Latitude']= np.ma.vstack((gvars['IMAGER']['Latitude'],lt))
                    gvars['IMAGER']['Longitude']= np.ma.vstack((gvars['IMAGER']['Longitude'],lg))
                    datavars['IMAGER']['ch08']= np.ma.vstack((datavars['IMAGER']['ch08'],ch08))
                    datavars['IMAGER']['ch09']= np.ma.vstack((datavars['IMAGER']['ch09'],ch09))
                    datavars['IMAGER']['ch10']= np.ma.vstack((datavars['IMAGER']['ch10'],ch10))
                    datavars['IMAGER']['ch11']= np.ma.vstack((datavars['IMAGER']['ch11'],ch11))
                    datavars['IMAGER']['ch17']= np.ma.vstack((datavars['IMAGER']['ch17'],ch17))
                    datavars['IMAGER']['ch18']= np.ma.vstack((datavars['IMAGER']['ch18'],ch18))
                    datavars['IMAGER']['surface']= np.ma.vstack((datavars['IMAGER']['surface'],surf))
                    datavars['IMAGER']['rain']= np.ma.vstack((datavars['IMAGER']['rain'],rain))
                    gvars['IMAGER']['Latitude']= np.ma.masked_values(gvars['IMAGER']['Latitude'],bad_value)
                    gvars['IMAGER']['Longitude']= np.ma.masked_values(gvars['IMAGER']['Longitude'],bad_value)
                    datavars['IMAGER']['ch08']= np.ma.masked_values(datavars['IMAGER']['ch08'],bad_value)
                    datavars['IMAGER']['ch09']= np.ma.masked_values(datavars['IMAGER']['ch09'],bad_value)
                    datavars['IMAGER']['ch10']= np.ma.masked_values(datavars['IMAGER']['ch10'],bad_value)
                    datavars['IMAGER']['ch11']= np.ma.masked_values(datavars['IMAGER']['ch11'],bad_value)
                    datavars['IMAGER']['ch17']= np.ma.masked_values(datavars['IMAGER']['ch17'],bad_value)
                    datavars['IMAGER']['ch18']= np.ma.masked_values(datavars['IMAGER']['ch18'],bad_value)
                    datavars['IMAGER']['surface']= np.ma.masked_values(datavars['IMAGER']['surface'],bad_value)
                    datavars['IMAGER']['rain']= np.ma.masked_values(datavars['IMAGER']['rain'],bad_value)
            #bufch08 = datavars['IMAGER']['ch08']
            #datavars['IMAGER']['ch08'] = bufch08
            #if nn==49:
            #    shell()
#-----------------------------------------------------------------------------------------
            enviro_read= np.ma.zeros((nscan_enviro,90))
            np.ma.masked_all_like(enviro_read)
            if scenecounts_enviro[0] < 0:
                print "ENVIRO is negative"
                #shell()
            lt = np.ma.masked_equal(enviro_read,bad_value)
            lg = np.ma.masked_equal(enviro_read,bad_value)
            ch12o = np.ma.masked_equal(enviro_read,bad_value)
            ch13o = np.ma.masked_equal(enviro_read,bad_value)
            ch14o = np.ma.masked_equal(enviro_read,bad_value)
            ch15o = np.ma.masked_equal(enviro_read,bad_value)
            ch16o = np.ma.masked_equal(enviro_read,bad_value)
            ch15_5x5 = np.ma.masked_equal(enviro_read,bad_value)
            ch16_5x5 = np.ma.masked_equal(enviro_read,bad_value)
            ch17_5x5 = np.ma.masked_equal(enviro_read,bad_value)
            ch18_5x5o = np.ma.masked_equal(enviro_read,bad_value)
            ch17_5x4 = np.ma.masked_equal(enviro_read,bad_value)
            ch18_5x4 = np.ma.masked_equal(enviro_read,bad_value)

            #shell()
            #ENVIROODD READ DATA
            for ii in range(nscan_enviro):
                if ii%2==0:
                    if start_scantime_enviro[ii] == -999:
                        print 'value of enviro odd scan is %d'% ii
                        continue
                    for jj in range(scenecounts_enviro[0]):
                        enviroodd_lat,enviroodd_lon,enviroodd_scene= np.fromstring(f1.read(6),dtype=np.dtype('short')).byteswap()
                        enviroodd_seaice,enviroodd_surf= np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
                        enviroodd_ch12,enviroodd_ch13,enviroodd_ch14,enviroodd_ch15,enviroodd_ch16,enviroodd_ch15_5x5,enviroodd_ch16_5x5,enviroodd_ch17_5x5,enviroodd_ch18_5x5,enviroodd_ch17_5x4,enviroodd_ch18_5x4= np.fromstring(f1.read(22),dtype=np.dtype('short')).byteswap()
                        enviroodd_rain1,enviroodd_rain2= np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
                        edr_bitflags= np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
                        nbytes+= 36
                        lat= 0.01*enviroodd_lat
                        lon= 0.01*enviroodd_lon
                        lt[ii][jj] = lat
                        lg[ii][jj]= lon
                        ch12o[ii][jj] = enviroodd_ch12
                        ch13o[ii][jj] = enviroodd_ch13
                        ch14o[ii][jj] = enviroodd_ch14
                        ch15o[ii][jj] = enviroodd_ch15
                        ch16o[ii][jj] = enviroodd_ch16
                        ch15_5x5[ii][jj] = enviroodd_ch15_5x5
                        ch16_5x5[ii][jj] = enviroodd_ch16_5x5
                        ch17_5x5[ii][jj] = enviroodd_ch17_5x5
                        ch18_5x5o[ii][jj] = enviroodd_ch18_5x5
                        ch17_5x4[ii][jj] = enviroodd_ch17_5x4
                        ch18_5x4[ii][jj] = enviroodd_ch18_5x4
            if 'Latitude' not in gvars['ENVIROODD'].keys():
                        gvars['ENVIROODD']['Latitude']= lt
                        gvars['ENVIROODD']['Longitude']= lg
                        datavars['ENVIROODD']['ch12']=ch12o 
                        datavars['ENVIROODD']['ch13']=ch13o 
                        datavars['ENVIROODD']['ch14']=ch14o
                        datavars['ENVIROODD']['ch15']=ch15o 
                        datavars['ENVIROODD']['ch16']=ch16o
                        datavars['ENVIROODD']['ch15_5x5'] =ch15_5x5 
                        datavars['ENVIROODD']['ch16_5x5'] =ch16_5x5 
                        datavars['ENVIROODD']['ch17_5x5'] =ch17_5x5 
                        datavars['ENVIROODD']['ch18_5x5o'] =ch18_5x5o 
                        datavars['ENVIROODD']['ch17_5x4'] =ch17_5x4 
                        datavars['ENVIROODD']['ch18_5x4'] =ch18_5x4 
            else:
                        gvars['ENVIROODD']['Latitude']= np.ma.vstack((gvars['ENVIROODD']['Latitude'],lt))
                        gvars['ENVIROODD']['Longitude']= np.ma.vstack((gvars['ENVIROODD']['Longitude'],lg))
                        datavars['ENVIROODD']['ch12']= np.ma.vstack((datavars['ENVIROODD']['ch12'],ch12o))
                        datavars['ENVIROODD']['ch13']= np.ma.vstack((datavars['ENVIROODD']['ch13'],ch13o))
                        datavars['ENVIROODD']['ch14']= np.ma.vstack((datavars['ENVIROODD']['ch14'],ch14o))
                        datavars['ENVIROODD']['ch15']= np.ma.vstack((datavars['ENVIROODD']['ch15'],ch15o))
                        datavars['ENVIROODD']['ch16']= np.ma.vstack((datavars['ENVIROODD']['ch16'],ch16o))
                        datavars['ENVIROODD']['ch15_5x5']= np.ma.vstack((datavars['ENVIROODD']['ch15_5x5'],ch15_5x5))
                        datavars['ENVIROODD']['ch16_5x5']= np.ma.vstack((datavars['ENVIROODD']['ch16_5x5'],ch16_5x5))
                        datavars['ENVIROODD']['ch17_5x5']= np.ma.vstack((datavars['ENVIROODD']['ch17_5x5'],ch17_5x5))
                        datavars['ENVIROODD']['ch18_5x5o']= np.ma.vstack((datavars['ENVIROODD']['ch18_5x5o'],ch18_5x5o))
                        datavars['ENVIROODD']['ch17_5x4']= np.ma.vstack((datavars['ENVIROODD']['ch17_5x4'],ch17_5x4))
                        datavars['ENVIROODD']['ch18_5x4']= np.ma.vstack((datavars['ENVIROODD']['ch18_5x4'],ch18_5x4))
                        gvars['ENVIROODD']['Latitude']= np.ma.masked_equal(gvars['ENVIROODD']['Latitude'],bad_value)
                        gvars['ENVIROODD']['Longitude']= np.ma.masked_equal(gvars['ENVIROODD']['Longitude'],bad_value)
                        datavars['ENVIROODD']['ch12']= np.ma.masked_equal(datavars['ENVIROODD']['ch12'],bad_value)
                        datavars['ENVIROODD']['ch13']= np.ma.masked_equal(datavars['ENVIROODD']['ch13'],bad_value)
                        datavars['ENVIROODD']['ch14']= np.ma.masked_equal(datavars['ENVIROODD']['ch14'],bad_value)
                        datavars['ENVIROODD']['ch15']= np.ma.masked_equal(datavars['ENVIROODD']['ch15'],bad_value)
                        datavars['ENVIROODD']['ch16']= np.ma.masked_equal(datavars['ENVIROODD']['ch16'],bad_value)
                        datavars['ENVIROODD']['ch15_5x5']= np.ma.masked_equal(datavars['ENVIROODD']['ch15_5x5'],bad_value)
                        datavars['ENVIROODD']['ch16_5x5']= np.ma.masked_equal(datavars['ENVIROODD']['ch16_5x5'],bad_value)
                        datavars['ENVIROODD']['ch17_5x5']= np.ma.masked_equal(datavars['ENVIROODD']['ch17_5x5'],bad_value)
                        datavars['ENVIROODD']['ch18_5x5o']= np.ma.masked_equal(datavars['ENVIROODD']['ch18_5x5o'],bad_value)
                        datavars['ENVIROODD']['ch17_5x4']= np.ma.masked_equal(datavars['ENVIROODD']['ch17_5x4'],bad_value)
                        datavars['ENVIROODD']['ch18_5x4']= np.ma.masked_equal(datavars['ENVIROODD']['ch18_5x4'],bad_value)
#-----------------------------------------------------------------------------------------
            if scenecounts_enviro[0] < 0:
                print "ENVIRO EVEN is negative"
                #shell()
            lt = np.ma.masked_equal(enviro_read,bad_value)
            lg = np.ma.masked_equal(enviro_read,bad_value)
            ch12e = np.ma.masked_equal(enviro_read,bad_value)
            ch13e = np.ma.masked_equal(enviro_read,bad_value)
            ch14e = np.ma.masked_equal(enviro_read,bad_value)
            ch15e = np.ma.masked_equal(enviro_read,bad_value)
            ch16e = np.ma.masked_equal(enviro_read,bad_value)
            
            #ENVIROEVEN READ DATA
            for ii in range(nscan_enviro):
                if ii%2==1:
                    if start_scantime_enviro[ii] == -999:
                        print 'value of enviro even scan is %d'% ii
                        continue
                    for jj in range(scenecounts_enviro[0]):
                        enviroeven_lat,enviroeven_lon,enviroeven_scene= np.fromstring(f1.read(6),dtype=np.dtype('short')).byteswap()
                        enviroeven_seaice,enviroeven_surf= np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
                        enviroeven_ch12,enviroeven_ch13,enviroeven_ch14,enviroeven_ch15,enviroeven_ch16= np.fromstring(f1.read(10),dtype=np.dtype('short')).byteswap()
                        nbytes+= 18
                        lat= 0.01*enviroeven_lat
                        lon= 0.01*enviroeven_lon
                        lt[ii][jj] = lat
                        lg[ii][jj] = lon
                        ch12e[ii][jj] = enviroeven_ch12
                        ch13e[ii][jj] = enviroeven_ch13
                        ch14e[ii][jj] = enviroeven_ch14
                        ch15e[ii][jj] = enviroeven_ch15
                        ch16e[ii][jj] = enviroeven_ch16
            if 'Latitude' not in gvars['ENVIROEVEN'].keys():
                        gvars['ENVIROEVEN']['Latitude'] = lt
                        gvars['ENVIROEVEN']['Longitude']= lg
                        datavars['ENVIROEVEN']['ch12e'] = ch12e
                        datavars['ENVIROEVEN']['ch13e'] = ch13e
                        datavars['ENVIROEVEN']['ch14e'] = ch14e
                        datavars['ENVIROEVEN']['ch15e'] = ch15e
                        datavars['ENVIROEVEN']['ch16e'] = ch16e
            else:
                        gvars['ENVIROEVEN']['Latitude']= np.ma.vstack((gvars['ENVIROEVEN']['Latitude'],lt)) 
                        gvars['ENVIROEVEN']['Longitude']= np.ma.vstack((gvars['ENVIROEVEN']['Longitude'],lg))
                        datavars['ENVIROEVEN']['ch12e']= np.ma.vstack((datavars['ENVIROEVEN']['ch12e'],ch12e))
                        datavars['ENVIROEVEN']['ch13e']= np.ma.vstack((datavars['ENVIROEVEN']['ch13e'],ch13e))
                        datavars['ENVIROEVEN']['ch14e']= np.ma.vstack((datavars['ENVIROEVEN']['ch14e'],ch14e))
                        datavars['ENVIROEVEN']['ch15e']= np.ma.vstack((datavars['ENVIROEVEN']['ch15e'],ch15e))
                        datavars['ENVIROEVEN']['ch16e']= np.ma.vstack((datavars['ENVIROEVEN']['ch16e'],ch16e))
                        gvars['ENVIROEVEN']['Latitude']= np.ma.masked_equal(gvars['ENVIROEVEN']['Latitude'],bad_value)
                        gvars['ENVIROEVEN']['Longitude']= np.ma.masked_equal(gvars['ENVIROEVEN']['Longitude'],bad_value)
                        datavars['ENVIROEVEN']['ch12e']= np.ma.masked_equal(datavars['ENVIROEVEN']['ch12e'],bad_value)
                        datavars['ENVIROEVEN']['ch13e']= np.ma.masked_equal(datavars['ENVIROEVEN']['ch13e'],bad_value)
                        datavars['ENVIROEVEN']['ch14e']= np.ma.masked_equal(datavars['ENVIROEVEN']['ch14e'],bad_value)
                        datavars['ENVIROEVEN']['ch15e']= np.ma.masked_equal(datavars['ENVIROEVEN']['ch15e'],bad_value)
                        datavars['ENVIROEVEN']['ch16e']= np.ma.masked_equal(datavars['ENVIROEVEN']['ch16e'],bad_value)
                        #if nn == 118:
                        #    shell()
#---------------------------------------------------------------------------------------------
            las_read= np.ma.zeros((nscan_las,60))
            np.ma.masked_all_like(las_read)
            if scenecounts_las[0] < 0:
                print "LAS is negative"
                #shell()
            lt = np.ma.masked_equal(las_read,bad_value)
            lg = np.ma.masked_equal(las_read,bad_value)
            ch01_3x3 = np.ma.masked_equal(las_read,bad_value)
            ch02_3x3 = np.ma.masked_equal(las_read,bad_value)
            ch03_3x3 = np.ma.masked_equal(las_read,bad_value)
            ch04_3x3 = np.ma.masked_equal(las_read,bad_value)
            ch05_3x3 = np.ma.masked_equal(las_read,bad_value)
            ch06_3x3 = np.ma.masked_equal(las_read,bad_value)
            ch07_3x3 = np.ma.masked_equal(las_read,bad_value)
            ch08_5x5 = np.ma.masked_equal(las_read,bad_value)
            ch09_5x5 = np.ma.masked_equal(las_read,bad_value)
            ch10_5x5 = np.ma.masked_equal(las_read,bad_value)
            ch11_5x5 = np.ma.masked_equal(las_read,bad_value)
            ch18_5x5 = np.ma.masked_equal(las_read,bad_value)
            ch24_3x3 = np.ma.masked_equal(las_read,bad_value)
            height_1000mb = np.ma.masked_equal(las_read,bad_value)
            surf = np.ma.masked_equal(las_read,bad_value)

            #shell()
            #LAS READ DATA
            for ii in range(nscan_las):
                if start_scantime_las[ii] == -999:
                    print 'value of las scan is %d'% ii
                    continue
                for jj in range(scenecounts_las[0]):
                    #if nn == 118 and jj == 7:
                    #    shell()
                    try:
                        las_lati,las_long,las_ch01_3x3,las_ch02_3x3,las_ch03_3x3,las_ch04_3x3,las_ch05_3x3,las_ch06_3x3,las_ch07_3x3,las_ch08_5x5,las_ch09_5x5,las_ch10_5x5,las_ch11_5x5,las_ch18_5x5,las_ch24_3x3,las_height_1000mb,las_surf= np.fromstring(f1.read(34),dtype=np.dtype('short')).byteswap()
                        las_tqflag,las_hqflag= np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
                        las_terrain,las_scene= np.fromstring(f1.read(4),dtype=np.dtype('short')).byteswap()
                    except:
                        continue
                    lat= 0.01*las_lati
                    lon= 0.01*las_long
                    nbytes+= 40
                    #shell()
                    lt[ii][jj] = lat
                    lg[ii][jj] = lon
                    ch01_3x3[ii][jj] = las_ch01_3x3
                    ch02_3x3[ii][jj] = las_ch02_3x3
                    ch03_3x3[ii][jj] = las_ch03_3x3
                    ch04_3x3[ii][jj] = las_ch04_3x3
                    ch05_3x3[ii][jj] = las_ch05_3x3
                    ch06_3x3[ii][jj] = las_ch06_3x3
                    ch07_3x3[ii][jj] = las_ch07_3x3
                    ch08_5x5[ii][jj] = las_ch08_5x5
                    ch09_5x5[ii][jj] = las_ch09_5x5
                    ch10_5x5[ii][jj] = las_ch10_5x5
                    ch11_5x5[ii][jj] = las_ch11_5x5
                    ch18_5x5[ii][jj] = las_ch18_5x5
                    ch24_3x3[ii][jj] = las_ch24_3x3
                    height_1000mb[ii][jj] = las_height_1000mb
                    surf[ii][jj] = las_surf
            if 'Latitude' not in gvars['LAS'].keys():
                    gvars['LAS']['Latitude']= lt
                    gvars['LAS']['Longitude']= lg
                    datavars['LAS']['ch01_3x3']=ch01_3x3
                    datavars['LAS']['ch02_3x3']=ch02_3x3
                    datavars['LAS']['ch03_3x3']=ch03_3x3
                    datavars['LAS']['ch04_3x3']=ch04_3x3
                    datavars['LAS']['ch05_3x3']=ch05_3x3
                    datavars['LAS']['ch06_3x3']=ch06_3x3
                    datavars['LAS']['ch07_3x3']=ch07_3x3
                    datavars['LAS']['ch08_5x5']=ch08_5x5
                    datavars['LAS']['ch09_5x5']=ch09_5x5
                    datavars['LAS']['ch10_5x5']=ch10_5x5
                    datavars['LAS']['ch11_5x5']=ch11_5x5
                    datavars['LAS']['ch18_5x5']=ch18_5x5
                    datavars['LAS']['ch24_3x3']=ch24_3x3
                    datavars['LAS']['height_1000mb'] = height_1000mb
                    datavars['LAS']['surf'] = surf
            else:
                    gvars['LAS']['Latitude']= np.ma.vstack((gvars['LAS']['Latitude'],lt))
                    gvars['LAS']['Longitude']= np.ma.vstack((gvars['LAS']['Longitude'],lg))
                    datavars['LAS']['ch01_3x3']= np.ma.vstack((datavars['LAS']['ch01_3x3'],ch01_3x3))
                    datavars['LAS']['ch02_3x3']= np.ma.vstack((datavars['LAS']['ch02_3x3'],ch02_3x3))
                    datavars['LAS']['ch03_3x3']= np.ma.vstack((datavars['LAS']['ch03_3x3'],ch03_3x3))
                    datavars['LAS']['ch04_3x3']= np.ma.vstack((datavars['LAS']['ch04_3x3'],ch04_3x3))
                    datavars['LAS']['ch05_3x3']= np.ma.vstack((datavars['LAS']['ch05_3x3'],ch05_3x3))
                    datavars['LAS']['ch06_3x3']= np.ma.vstack((datavars['LAS']['ch06_3x3'],ch06_3x3))
                    datavars['LAS']['ch07_3x3']= np.ma.vstack((datavars['LAS']['ch07_3x3'],ch07_3x3))
                    datavars['LAS']['ch08_5x5']= np.ma.vstack((datavars['LAS']['ch08_5x5'],ch08_5x5))
                    datavars['LAS']['ch09_5x5']= np.ma.vstack((datavars['LAS']['ch09_5x5'],ch09_5x5))
                    datavars['LAS']['ch10_5x5']= np.ma.vstack((datavars['LAS']['ch10_5x5'],ch10_5x5))
                    datavars['LAS']['ch11_5x5']= np.ma.vstack((datavars['LAS']['ch11_5x5'],ch11_5x5))
                    datavars['LAS']['ch18_5x5']= np.ma.vstack((datavars['LAS']['ch18_5x5'],ch18_5x5))
                    datavars['LAS']['ch24_3x3']= np.ma.vstack((datavars['LAS']['ch24_3x3'],ch24_3x3))
                    datavars['LAS']['height_1000mb']= np.ma.vstack((datavars['LAS']['height_1000mb'],height_1000mb))
                    datavars['LAS']['surf']= np.ma.vstack((datavars['LAS']['surf'],surf))
                    gvars['LAS']['Latitude']= np.ma.masked_equal(gvars['LAS']['Latitude'],bad_value)
                    gvars['LAS']['Longitude']= np.ma.masked_equal(gvars['LAS']['Longitude'],bad_value)
                    datavars['LAS']['ch01_3x3']= np.ma.masked_equal(datavars['LAS']['ch01_3x3'],bad_value)
                    datavars['LAS']['ch02_3x3']= np.ma.masked_equal(datavars['LAS']['ch02_3x3'],bad_value)
                    datavars['LAS']['ch03_3x3']= np.ma.masked_equal(datavars['LAS']['ch03_3x3'],bad_value)
                    datavars['LAS']['ch04_3x3']= np.ma.masked_equal(datavars['LAS']['ch04_3x3'],bad_value)
                    datavars['LAS']['ch05_3x3']= np.ma.masked_equal(datavars['LAS']['ch05_3x3'],bad_value)
                    datavars['LAS']['ch06_3x3']= np.ma.masked_equal(datavars['LAS']['ch06_3x3'],bad_value)
                    datavars['LAS']['ch07_3x3']= np.ma.masked_equal(datavars['LAS']['ch07_3x3'],bad_value)
                    datavars['LAS']['ch08_5x5']= np.ma.masked_equal(datavars['LAS']['ch08_5x5'],bad_value)
                    datavars['LAS']['ch09_5x5']= np.ma.masked_equal(datavars['LAS']['ch09_5x5'],bad_value)
                    datavars['LAS']['ch10_5x5']= np.ma.masked_equal(datavars['LAS']['ch10_5x5'],bad_value)
                    datavars['LAS']['ch11_5x5']= np.ma.masked_equal(datavars['LAS']['ch11_5x5'],bad_value)
                    datavars['LAS']['ch18_5x5']= np.ma.masked_equal(datavars['LAS']['ch18_5x5'],bad_value)
                    datavars['LAS']['ch24_3x3']= np.ma.masked_equal(datavars['LAS']['ch24_3x3'],bad_value)
                    datavars['LAS']['height_1000mb']= np.ma.masked_equal(datavars['LAS']['height_1000mb'],bad_value)
                    datavars['LAS']['surf']= np.ma.masked_equal(datavars['LAS']['surf'],bad_value)
                    #if nn==118 and jj==7:
                    #    shell()
#---------------------------------------------------------------------------------
            uas_read= np.ma.zeros((nscan_uas,30))
            np.ma.masked_all_like(uas_read)
            if scenecounts_uas[0] < 0:
                print "UAS is negative"
                #shell()
            lt = np.ma.masked_equal(uas_read,bad_value)
            lg = np.ma.masked_equal(uas_read,bad_value)
            ch19_6x6 = np.ma.masked_equal(uas_read,bad_value)
            ch20_6x6 = np.ma.masked_equal(uas_read,bad_value)
            ch21_6x6 = np.ma.masked_equal(uas_read,bad_value)
            ch22_6x6 = np.ma.masked_equal(uas_read,bad_value)
            ch23_6x6 = np.ma.masked_equal(uas_read,bad_value)
            ch24_6x6 = np.ma.masked_equal(uas_read,bad_value)
            sceneu = np.ma.masked_equal(uas_read,bad_value)
            tqflag = np.ma.masked_equal(uas_read,bad_value)

            #shell()
            #UAS READ DATA
            for ii in range(nscan_uas):
                if start_scantime_uas[ii] == -999:
                    print 'value of uas scan is %d'% ii
                    continue
                for jj in range(scenecounts_uas[0]):
                    uas_lat,uas_lon,uas_ch19_6x6,uas_ch20_6x6,uas_ch21_6x6,uas_ch22_6x6,uas_ch23_6x6,uas_ch24_6x6,uas_scene,uas_tqflag= np.fromstring(f1.read(20),dtype=np.dtype('short')).byteswap()
                    uas_field,uas_bdotk2= np.fromstring(f1.read(8),dtype=np.dtype('int32')).byteswap()
                    nbytes+= 28
                    lat= 0.01*uas_lat
                    lon= 0.01*uas_lon
                    lt[ii][jj]= lat
                    lg[ii][jj]= lon
                    ch19_6x6[ii][jj] = uas_ch19_6x6
                    ch20_6x6[ii][jj] = uas_ch20_6x6
                    ch21_6x6[ii][jj] = uas_ch21_6x6
                    ch22_6x6[ii][jj] = uas_ch22_6x6
                    ch23_6x6[ii][jj] = uas_ch23_6x6
                    ch24_6x6[ii][jj] = uas_ch24_6x6
                    sceneu[ii][jj] = uas_scene
                    tqflag[ii][jj] = uas_tqflag
            if 'Latitude' not in gvars['UAS'].keys():
                    gvars['UAS']['Latitude']= lt
                    gvars['UAS']['Longitude']= lg
                    datavars['UAS']['ch19_6x6']=ch19_6x6
                    datavars['UAS']['ch20_6x6']=ch20_6x6
                    datavars['UAS']['ch21_6x6']=ch21_6x6
                    datavars['UAS']['ch22_6x6']=ch22_6x6
                    datavars['UAS']['ch23_6x6']=ch23_6x6
                    datavars['UAS']['ch24_6x6']=ch24_6x6
                    datavars['UAS']['scene']= sceneu
                    datavars['UAS']['uas_tqflag']=tqflag
            else:
                    gvars['UAS']['Latitude']= np.ma.vstack((gvars['UAS']['Latitude'],lt)) 
                    gvars['UAS']['Longitude']= np.ma.vstack((gvars['UAS']['Longitude'],lg))
                    datavars['UAS']['ch19_6x6']= np.ma.vstack((datavars['UAS']['ch19_6x6'],ch19_6x6))
                    datavars['UAS']['ch20_6x6']= np.ma.vstack((datavars['UAS']['ch20_6x6'],ch20_6x6))
                    datavars['UAS']['ch21_6x6']= np.ma.vstack((datavars['UAS']['ch21_6x6'],ch21_6x6))
                    datavars['UAS']['ch22_6x6']= np.ma.vstack((datavars['UAS']['ch22_6x6'],ch22_6x6))
                    datavars['UAS']['ch23_6x6']= np.ma.vstack((datavars['UAS']['ch23_6x6'],ch23_6x6))
                    datavars['UAS']['ch24_6x6']= np.ma.vstack((datavars['UAS']['ch24_6x6'],ch24_6x6))
                    datavars['UAS']['scene']= np.ma.vstack((datavars['UAS']['scene'],sceneu))
                    datavars['UAS']['uas_tqflag']= np.ma.vstack((datavars['UAS']['uas_tqflag'],tqflag))
                    gvars['UAS']['Latitude']= np.ma.masked_equal(gvars['UAS']['Latitude'],bad_value)
                    gvars['UAS']['Longitude']= np.ma.masked_equal(gvars['UAS']['Longitude'],bad_value)
                    datavars['UAS']['ch19_6x6']= np.ma.masked_equal(datavars['UAS']['ch19_6x6'],bad_value)
                    datavars['UAS']['ch20_6x6']= np.ma.masked_equal(datavars['UAS']['ch20_6x6'],bad_value)
                    datavars['UAS']['ch21_6x6']= np.ma.masked_equal(datavars['UAS']['ch21_6x6'],bad_value)
                    datavars['UAS']['ch22_6x6']= np.ma.masked_equal(datavars['UAS']['ch22_6x6'],bad_value)
                    datavars['UAS']['ch23_6x6']= np.ma.masked_equal(datavars['UAS']['ch23_6x6'],bad_value)
                    datavars['UAS']['ch24_6x6']= np.ma.masked_equal(datavars['UAS']['ch24_6x6'],bad_value)
                    datavars['UAS']['scene']= np.ma.masked_equal(datavars['UAS']['scene'],bad_value)
                    datavars['UAS']['uas_tqflag']= np.ma.masked_equal(datavars['UAS']['uas_tqflag'],bad_value)
            
            nfiller= 512 - ( nbytes % 512 )
            #These are hard coded nfiller values.  This was done due to several lines of data missing
            #within the binary file.  We need to figure out the magic number on how manys lines of
            #missing data vs. the number of nfiller bytes that need to be added 
            if nbytes == 158340:
                nfiller = 1916
            if nbytes == 142980:
                nfiller = 2940
            if nbytes == 145200:
                nfiller = 17104
            try:
                filler_bytes= np.fromstring(f1.read(nfiller),dtype=np.dtype('int8')).byteswap()[0]
            except:
                continue
            #if nn==33:
            #    print "Shell in nbytes test loop"
            #    shell()
        #Check for timegaps to identify missing lines
        for mm in range(nsdr*24):
            sec= 86400.0*bufdate[mm] + buftime[mm]
            sec_prev= sec-1.899
            lines= ((sec - sec_prev)/1.899) + 0.5
        #if nn==47:
        #    print 'Shell in time test loop'
        #    shell()
#-----------------------------------------------------------------------------------------------------
        # Loop through each dataset name found in the dataset_info property above.
        for dsname in self.dataset_info.keys():
            for geoipsvarname,dfvarname in self.dataset_info[dsname].items():
                log.info('    Reading '+dsname+' channel "'+dfvarname+'" from file into SciFile channel: "'+geoipsvarname+'"...')
                #shell()
                data = datavars[dsname][geoipsvarname]
                fillvalue = -999
                datavars[dsname][geoipsvarname] = (np.ma.masked_equal(data,fillvalue)/100) + 273.15
        #shell()
        # Loop through each dataset name found in the gvar_info property above.
        for dsname in self.gvar_info.keys():
            for geoipsvarname,dfvarname in self.gvar_info[dsname].items():
                log.info('    Reading '+dsname+' channel "'+dfvarname+'" from file into SciFile channel: "'+geoipsvarname+'"...')
                #shell()
                data = gvars[dsname][geoipsvarname]
                fillvalue = -999
                gvars[dsname][geoipsvarname] = np.ma.masked_equal(data,fillvalue)
        #shell()
