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
                     'ENVIRO': {'ch12':'ch12',
                              'ch13':'ch13',
                              'ch14':'ch14',
                              'ch15':'ch15',
                              'ch16':'ch16',
                              'ch15_5x5':'ch15_5x5',
                              'ch16_5x5':'ch16_5x5',
                              'ch17_5x5':'ch17_5x5',
                              'ch18_5x5':'ch18_5x5',
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
                  'ENVIRO': {
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

        #Calling in the individual bytes to check the header
        f1 = open(fname,'rb')
        sw_rev = np.fromstring(f1.read(2),dtype=np.dtype('short')).byteswap()[0]
        endian,fileid = np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
        rev = np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
        year = np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
        jday = np.fromstring(f1.read(2),dtype=np.dtype('short')).byteswap()
        hour,minu = np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
        satid,nsdr = np.fromstring(f1.read(4),dtype=np.dtype('short')).byteswap()
        spare1,spare2,spare3= np.fromstring(f1.read(3),dtype=np.dtype('int8')).byteswap()
        proc_stat_flags = np.fromstring(f1.read(1),dtype=np.dtype('int8')).byteswap()
        spare4= np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
        f1.close()

        if year > 1900 and year <4000 and \
           jday >=1 and jday <=366 and \
           hour >=0 and hour <=25 and \
           minu >=0 and minu <=59:
            return True
        return False


    def read(self,fname,datavars,gvars,metadata,chans=None,sector_definition=None):

        f1 = open(fname,'rb')

        #READ HEARDER
        sw_rev = np.fromstring(f1.read(2),dtype=np.dtype('short')).byteswap()[0]
        endian,fileid = np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
        rev = np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
        year = np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
        jday = np.fromstring(f1.read(2),dtype=np.dtype('short')).byteswap()
        hour,minu = np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
        satid,nsdr = np.fromstring(f1.read(4),dtype=np.dtype('short')).byteswap()
        spare1,spare2,spare3= np.fromstring(f1.read(3),dtype=np.dtype('int8')).byteswap()
        proc_stat_flags = np.fromstring(f1.read(1),dtype=np.dtype('int8')).byteswap()
        spare4= np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
        #Need to set up time to be read in by the metadata (year and jday are arrays)
        time= '%04d%03d%02d%02d' % (year[0],jday[0],hour,minu)
        nbytes=28 #bytes that have been read in
        #Read scan records at 512-byte boundaries
        nfiller= 512- (nbytes % 512)  # skip nfiller bytes so that the scan header will start at the 513th byte of the data records, 
        filler_bytes= np.fromstring(f1.read(nfiller),dtype=np.dtype('int8')).byteswap()

        # Rev 6A of the SSMIS SDR software changed the scalling of channel 12-16 to 100 (it was 10 before this change)
        #     effective with orbit rev 12216 for F-16 and thereafter for all future satellites
        rev6a=1
        if satid==1 and rev[0] < 12216:
           rev6a=0   

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

        #Enter metadata
        metadata['top']['start_datetime'] = datetime.strptime(time,'%Y%j%H%M')
        metadata['top']['end_datetime'] = datetime.strptime(time,'%Y%j%H%M')
        metadata['top']['dataprovider'] = 'DMSP'
        metadata['top']['filename_datetime'] = metadata['top']['start_datetime']
        metadata['top']['platform_name'] = satid
        metadata['top']['source_name'] = 'ssmis'
        si = SatSensorInfo(metadata['top']['platform_name'],metadata['top']['source_name'])
        if not si:
            from ..scifileexceptions import SciFileError
            raise SciFileError('Unrecognized platform and source name combination: '+metadata['top']['platform_name']+' '+metadata['top']['source_name'])

        dfn = DataFileName(os.path.basename(fname))
        if dfn:
            sdfn = dfn.create_standard()
            metadata['top']['filename_datetime'] = sdfn.datetime

        # Tells driver to NOT try to sector this data.
        metadata['top']['NON_SECTORABLE'] = True

        if chans == []:
            return

        bad_value= -999

        for nn in range(nsdr):          #loop number of sdr data records
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
            nbytes+= 360   #total bytes of the scan header
            nscan0 = scan - 1
#-----------------------------------------------------------------------------------------
            try:
                imager_read= np.ma.zeros((nscan_imager,180))
                np.ma.masked_all_like(imager_read)
            except:
                print 'Shell dropped for imager_read'
            if scenecounts_imager[0] < 0 :
                print "IMAGER is negative"
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

            #IMAGER READ DATA
            for ii in range(nscan_imager):
                if start_scantime_imager[ii] == -999:
                    print 'value of imager scan is %d'% ii
                    continue
                for jj in range(scenecounts_imager[ii]):
                    imager_lat, imager_lon, imager_scene= np.fromstring(f1.read(6),dtype=np.dtype('short')).byteswap()
                    imager_surf, imager_rain= np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
                    imager_ch08,imager_ch09,imager_ch10,imager_ch11,imager_ch17,imager_ch18= np.fromstring(f1.read(12),dtype=np.dtype('short')).byteswap()
                    nbytes+= 20
                    k= 180*(nscan0+ii)+jj
                    lat= 0.01*imager_lat
                    lon= 0.01*imager_lon
                    try:
                        lt[ii][jj] = lat
                        lg[ii][jj] = lon
                        ch08[ii][jj] = imager_ch08    #150    Ghz
                        ch09[ii][jj] = imager_ch09    #183+-7
                        ch10[ii][jj] = imager_ch10    #183+-3
                        ch11[ii][jj] = imager_ch11    #183+-1
                        ch17[ii][jj] = imager_ch17    #91V
                        ch18[ii][jj] = imager_ch18    #91H
                        surf[ii][jj] = imager_surf
                        rain[ii][jj] = imager_rain
                    except:
                        print 'Failed setting arrays in scan_imager'
            
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
#-----------------------------------------------------------------------------------------
            enviro_read= np.ma.zeros((nscan_enviro,90))
            np.ma.masked_all_like(enviro_read)
            if scenecounts_enviro[0] < 0:
                print "ENVIRO is negative"
            lt = np.ma.masked_equal(enviro_read,bad_value)
            lg = np.ma.masked_equal(enviro_read,bad_value)
            ch12 = np.ma.masked_equal(enviro_read,bad_value)
            ch13 = np.ma.masked_equal(enviro_read,bad_value)
            ch14 = np.ma.masked_equal(enviro_read,bad_value)
            ch15 = np.ma.masked_equal(enviro_read,bad_value)
            ch16 = np.ma.masked_equal(enviro_read,bad_value)
            ch15_5x5 = np.ma.masked_equal(enviro_read,bad_value)
            ch16_5x5 = np.ma.masked_equal(enviro_read,bad_value)
            ch17_5x5 = np.ma.masked_equal(enviro_read,bad_value)
            ch18_5x5 = np.ma.masked_equal(enviro_read,bad_value)
            ch17_5x4 = np.ma.masked_equal(enviro_read,bad_value)
            ch18_5x4 = np.ma.masked_equal(enviro_read,bad_value)

            #ENVIRO READ DATA
            for ii in range(nscan_enviro):
                if ii%2==0:                   #for odd scan numbers
                    if start_scantime_enviro[ii] == -999:
                        print 'value of enviro odd scan is %d'% ii
                        continue
                    for jj in range(scenecounts_enviro[ii]):
                        enviroodd_lat,enviroodd_lon,enviroodd_scene= np.fromstring(f1.read(6),dtype=np.dtype('short')).byteswap()
                        enviroodd_seaice,enviroodd_surf= np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
                        enviroodd_ch12,enviroodd_ch13,enviroodd_ch14,enviroodd_ch15,enviroodd_ch16,enviroodd_ch15_5x5,enviroodd_ch16_5x5,enviroodd_ch17_5x5,enviroodd_ch18_5x5,enviroodd_ch17_5x4,enviroodd_ch18_5x4= np.fromstring(f1.read(22),dtype=np.dtype('short')).byteswap()
                        enviroodd_rain1,enviroodd_rain2= np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
                        edr_bitflags= np.fromstring(f1.read(4),dtype=np.dtype('int32')).byteswap()
                        nbytes+= 36
                        lat= 0.01*enviroodd_lat
                        lon= 0.01*enviroodd_lon
                        lt[ii][jj]= lat
                        lg[ii][jj]= lon
                        if rev6a == 1:
                           ch12[ii][jj] = enviroodd_ch12            #19H
                           ch13[ii][jj] = enviroodd_ch13            #19V
                           ch14[ii][jj] = enviroodd_ch14            #22V
                           ch15[ii][jj] = enviroodd_ch15            #37H
                           ch16[ii][jj] = enviroodd_ch16            #37V
                           ch15_5x5[ii][jj] = enviroodd_ch15_5x5
                           ch16_5x5[ii][jj] = enviroodd_ch16_5x5
                           ch17_5x5[ii][jj] = enviroodd_ch17_5x5
                           ch18_5x5[ii][jj] = enviroodd_ch18_5x5
                           ch17_5x4[ii][jj] = enviroodd_ch17_5x4
                           ch18_5x4[ii][jj] = enviroodd_ch18_5x4
                        else:
                           ch12[ii][jj] = 10*enviroodd_ch12
                           ch13[ii][jj] = 10*enviroodd_ch13
                           ch14[ii][jj] = 10*enviroodd_ch14
                           ch15[ii][jj] = 10*enviroodd_ch15
                           ch16[ii][jj] = 10*enviroodd_ch16
                           ch15_5x5[ii][jj] = 10*enviroodd_ch15_5x5
                           ch16_5x5[ii][jj] = 10*enviroodd_ch16_5x5
                           ch17_5x5[ii][jj] = 10*enviroodd_ch17_5x5
                           ch18_5x5[ii][jj] = 10*enviroodd_ch18_5x5
                           ch17_5x4[ii][jj] = 10*enviroodd_ch17_5x4
                           ch18_5x4[ii][jj] = 10*enviroodd_ch18_5x4

                if ii%2==1:              # for even scan numbers
                    if start_scantime_enviro[ii] == -999:
                        print 'value of enviro even scan is %d'% ii
                        continue
                    for jj in range(scenecounts_enviro[ii]):
                        enviroeven_lat,enviroeven_lon,enviroeven_scene= np.fromstring(f1.read(6),dtype=np.dtype('short')).byteswap()
                        enviroeven_seaice,enviroeven_surf= np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
                        enviroeven_ch12,enviroeven_ch13,enviroeven_ch14,enviroeven_ch15,enviroeven_ch16= np.fromstring(f1.read(10),dtype=np.dtype('short')).byteswap()
                        nbytes+= 18
                        lat= 0.01*enviroeven_lat
                        lon= 0.01*enviroeven_lon
                        lt[ii][jj] = lat
                        lg[ii][jj] = lon
                        if rev6a == 1:
                           ch12[ii][jj] = enviroeven_ch12
                           ch13[ii][jj] = enviroeven_ch13
                           ch14[ii][jj] = enviroeven_ch14
                           ch15[ii][jj] = enviroeven_ch15
                           ch16[ii][jj] = enviroeven_ch16
                        else:
                           ch12[ii][jj] = 10*enviroeven_ch12
                           ch13[ii][jj] = 10*enviroeven_ch13
                           ch14[ii][jj] = 10*enviroeven_ch14
                           ch15[ii][jj] = 10*enviroeven_ch15
                           ch16[ii][jj] = 10*enviroeven_ch16

            if 'Latitude' not in gvars['ENVIRO'].keys():
                        gvars['ENVIRO']['Latitude']= lt
                        gvars['ENVIRO']['Longitude']= lg
                        datavars['ENVIRO']['ch12']=ch12 
                        datavars['ENVIRO']['ch13']=ch13 
                        datavars['ENVIRO']['ch14']=ch14
                        datavars['ENVIRO']['ch15']=ch15 
                        datavars['ENVIRO']['ch16']=ch16
                        datavars['ENVIRO']['ch15_5x5'] =ch15_5x5 
                        datavars['ENVIRO']['ch16_5x5'] =ch16_5x5 
                        datavars['ENVIRO']['ch17_5x5'] =ch17_5x5 
                        datavars['ENVIRO']['ch18_5x5'] =ch18_5x5 
                        datavars['ENVIRO']['ch17_5x4'] =ch17_5x4 
                        datavars['ENVIRO']['ch18_5x4'] =ch18_5x4 
            else:
                        gvars['ENVIRO']['Latitude']= np.ma.vstack((gvars['ENVIRO']['Latitude'],lt))
                        gvars['ENVIRO']['Longitude']= np.ma.vstack((gvars['ENVIRO']['Longitude'],lg))
                        datavars['ENVIRO']['ch12']= np.ma.vstack((datavars['ENVIRO']['ch12'],ch12))
                        datavars['ENVIRO']['ch13']= np.ma.vstack((datavars['ENVIRO']['ch13'],ch13))
                        datavars['ENVIRO']['ch14']= np.ma.vstack((datavars['ENVIRO']['ch14'],ch14))
                        datavars['ENVIRO']['ch15']= np.ma.vstack((datavars['ENVIRO']['ch15'],ch15))
                        datavars['ENVIRO']['ch16']= np.ma.vstack((datavars['ENVIRO']['ch16'],ch16))
                        datavars['ENVIRO']['ch15_5x5']= np.ma.vstack((datavars['ENVIRO']['ch15_5x5'],ch15_5x5))
                        datavars['ENVIRO']['ch16_5x5']= np.ma.vstack((datavars['ENVIRO']['ch16_5x5'],ch16_5x5))
                        datavars['ENVIRO']['ch17_5x5']= np.ma.vstack((datavars['ENVIRO']['ch17_5x5'],ch17_5x5))
                        datavars['ENVIRO']['ch18_5x5']= np.ma.vstack((datavars['ENVIRO']['ch18_5x5'],ch18_5x5))
                        datavars['ENVIRO']['ch17_5x4']= np.ma.vstack((datavars['ENVIRO']['ch17_5x4'],ch17_5x4))
                        datavars['ENVIRO']['ch18_5x4']= np.ma.vstack((datavars['ENVIRO']['ch18_5x4'],ch18_5x4))
                        gvars['ENVIRO']['Latitude']= np.ma.masked_equal(gvars['ENVIRO']['Latitude'],bad_value)
                        gvars['ENVIRO']['Longitude']= np.ma.masked_equal(gvars['ENVIRO']['Longitude'],bad_value)
                        datavars['ENVIRO']['ch12']= np.ma.masked_equal(datavars['ENVIRO']['ch12'],bad_value)
                        datavars['ENVIRO']['ch13']= np.ma.masked_equal(datavars['ENVIRO']['ch13'],bad_value)
                        datavars['ENVIRO']['ch14']= np.ma.masked_equal(datavars['ENVIRO']['ch14'],bad_value)
                        datavars['ENVIRO']['ch15']= np.ma.masked_equal(datavars['ENVIRO']['ch15'],bad_value)
                        datavars['ENVIRO']['ch16']= np.ma.masked_equal(datavars['ENVIRO']['ch16'],bad_value)
                        datavars['ENVIRO']['ch15_5x5']= np.ma.masked_equal(datavars['ENVIRO']['ch15_5x5'],bad_value)
                        datavars['ENVIRO']['ch16_5x5']= np.ma.masked_equal(datavars['ENVIRO']['ch16_5x5'],bad_value)
                        datavars['ENVIRO']['ch17_5x5']= np.ma.masked_equal(datavars['ENVIRO']['ch17_5x5'],bad_value)
                        datavars['ENVIRO']['ch18_5x5']= np.ma.masked_equal(datavars['ENVIRO']['ch18_5x5'],bad_value)
                        datavars['ENVIRO']['ch17_5x4']= np.ma.masked_equal(datavars['ENVIRO']['ch17_5x4'],bad_value)
                        datavars['ENVIRO']['ch18_5x4']= np.ma.masked_equal(datavars['ENVIRO']['ch18_5x4'],bad_value)
#-----------------------------------------------------------------------------------------
            las_read= np.ma.zeros((nscan_las,60))
            np.ma.masked_all_like(las_read)
            if scenecounts_las[0] < 0:
                print "LAS is negative"
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

            #LAS READ DATA
            for ii in range(nscan_las):
                if start_scantime_las[ii] == -999:
                    print 'value of las scan is %d'% ii
                    continue
                for jj in range(scenecounts_las[ii]):
                    try:
                        las_lati,las_long,las_ch01_3x3,las_ch02_3x3,las_ch03_3x3,las_ch04_3x3,las_ch05_3x3,las_ch06_3x3,las_ch07_3x3,las_ch08_5x5,las_ch09_5x5,las_ch10_5x5,las_ch11_5x5,las_ch18_5x5,las_ch24_3x3,las_height_1000mb,las_surf= np.fromstring(f1.read(34),dtype=np.dtype('short')).byteswap()
                        las_tqflag,las_hqflag= np.fromstring(f1.read(2),dtype=np.dtype('int8')).byteswap()
                        las_terrain,las_scene= np.fromstring(f1.read(4),dtype=np.dtype('short')).byteswap()
                    except:
                        continue
                    lat= 0.01*las_lati
                    lon= 0.01*las_long
                    nbytes+= 40
                    lt[ii][jj] = lat
                    lg[ii][jj] = lon
                    ch01_3x3[ii][jj] = las_ch01_3x3           #50.3 V
                    ch02_3x3[ii][jj] = las_ch02_3x3           #52.8 V
                    ch03_3x3[ii][jj] = las_ch03_3x3           #53.60V
                    ch04_3x3[ii][jj] = las_ch04_3x3           #54.4 V
                    ch05_3x3[ii][jj] = las_ch05_3x3           #55.5 V
                    ch06_3x3[ii][jj] = las_ch06_3x3           #57.3 RCP
                    ch07_3x3[ii][jj] = las_ch07_3x3           #59.4 RCP
                    ch08_5x5[ii][jj] = las_ch08_5x5           #150 H
                    ch09_5x5[ii][jj] = las_ch09_5x5           #183.31+-7 H
                    ch10_5x5[ii][jj] = las_ch10_5x5           #183.31+-3 H
                    ch11_5x5[ii][jj] = las_ch11_5x5           #183.31+-1 H
                    ch18_5x5[ii][jj] = las_ch18_5x5           #91 H
                    ch24_3x3[ii][jj] = las_ch24_3x3           #60.79+-36+-0.05 RCP
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
#---------------------------------------------------------------------------------
            uas_read= np.ma.zeros((nscan_uas,30))
            np.ma.masked_all_like(uas_read)
            if scenecounts_uas[0] < 0:
                print "UAS is negative"
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

            #UAS READ DATA
            for ii in range(nscan_uas):
                if start_scantime_uas[ii] == -999:
                    print 'value of uas scan is %d'% ii
                    continue
                for jj in range(scenecounts_uas[ii]):
                    uas_lat,uas_lon,uas_ch19_6x6,uas_ch20_6x6,uas_ch21_6x6,uas_ch22_6x6,uas_ch23_6x6,uas_ch24_6x6,uas_scene,uas_tqflag= np.fromstring(f1.read(20),dtype=np.dtype('short')).byteswap()
                    uas_field,uas_bdotk2= np.fromstring(f1.read(8),dtype=np.dtype('int32')).byteswap()
                    nbytes+= 28
                    lat= 0.01*uas_lat
                    lon= 0.01*uas_lon
                    lt[ii][jj]= lat
                    lg[ii][jj]= lon
                    ch19_6x6[ii][jj] = uas_ch19_6x6      #63.28+-0.28 RCP GHz
                    ch20_6x6[ii][jj] = uas_ch20_6x6      #60.79+-0.36 RCP
                    ch21_6x6[ii][jj] = uas_ch21_6x6      #60.79+-0.36+-0.002 RCP
                    ch22_6x6[ii][jj] = uas_ch22_6x6      #60.79+-0.36+-0.0055 RCP
                    ch23_6x6[ii][jj] = uas_ch23_6x6      #60.79+-0.36+-0.0016 RCP 
                    ch24_6x6[ii][jj] = uas_ch24_6x6      #60.79+-0.36+-0.050 RCP
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
           
            print 'nfiller=', nfiller 
            nfiller= 512 - ( nbytes % 512 )   # nfiller bytes to be skipped so that the next scan header will start at the 513th byte.
            try:
                filler_bytes= np.fromstring(f1.read(nfiller),dtype=np.dtype('int8')).byteswap()[0]
            except:
                continue
        f1.close()
#-----------------------------------------------------------------------------------------------------
        # Loop through each dataset name found in the dataset_info property above.
        for dsname in self.dataset_info.keys():
            for geoipsvarname,dfvarname in self.dataset_info[dsname].items():
                log.info('    Reading '+dsname+' channel "'+dfvarname+'" from file into SciFile channel: "'+geoipsvarname+'"...')
                #shell()
                data = datavars[dsname][geoipsvarname]
                fillvalue = -999
                datavars[dsname][geoipsvarname] = (np.ma.masked_equal(data,fillvalue)/100) + 273.15

        # Loop through each dataset name found in the gvar_info property above.
        for dsname in self.gvar_info.keys():
            for geoipsvarname,dfvarname in self.gvar_info[dsname].items():
                log.info('    Reading '+dsname+' channel "'+dfvarname+'" from file into SciFile channel: "'+geoipsvarname+'"...')
                #shell()
                data = gvars[dsname][geoipsvarname]
                fillvalue = -999
                gvars[dsname][geoipsvarname] = np.ma.masked_equal(data,fillvalue)
        #shell()
