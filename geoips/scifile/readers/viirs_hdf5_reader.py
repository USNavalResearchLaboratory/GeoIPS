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
from datetime import datetime
import logging
import os 
from glob import glob


# Installed Libraries
import h5py
import numpy as np
from numpy import asscalar as assc
from IPython import embed as shell


# GeoIPS Libraries
from ..scifileexceptions import SciFileError
from ..containers import DataSet, Variable, _empty_varinfo
from .reader import Reader

log = logging.getLogger(__name__)


def read_geolocation_file(fileobj,gvars,datavars,metadata,chans=None):
    #Get attributes required for reading
    dat_prod = fileobj['Data_Products'].keys()[0]
    attrs_elem = fileobj['Data_Products'][dat_prod]
    short_name = assc(attrs_elem.attrs['N_Collection_Short_Name'])
    datasettag = short_name.split('-')[1]

    #Get data and time elements
    data_elem = fileobj['All_Data'][short_name+'_All']
    
    # When granules are packaged together (ie, Class), we can't just 
    # go by Gran_0, only gives us time range for one granule, not all.
    # Need to look at all granules to get full time range.
    for gran_name in attrs_elem.keys():
        # Each granule's dataset is named such as VIIRS-DNB-GEO_Gran_0, VIIRS-DNB-GEO_Gran_1
        #   etc. Need to get full time range based on those, not just Gran_0 (which worked
        #   fine for our near real time data - not so much for CLASS which packages multiple
        #   granules together)

        # We do not want to use the _Aggr dataset - it only has instrument name,
        # etc. No start/end datetime
        if "Gran_" not in gran_name:
            continue
        time_elem = attrs_elem[gran_name]

        #Get time attributes. Need to get min startdt / max enddt from ALL granules
        start_date = assc(time_elem.attrs['Beginning_Date'])
        start_time = assc(time_elem.attrs['Beginning_Time'])
        currstartdt = datetime.strptime(start_date+start_time, '%Y%m%d%H%M%S.%fZ')
        if 'start_datetime' not in metadata['top'].keys() or not metadata['top']['start_datetime'] or currstartdt < metadata['top']['start_datetime']:
            metadata['top']['start_datetime'] = currstartdt

        end_date = assc(time_elem.attrs['Ending_Date'])
        end_time = assc(time_elem.attrs['Ending_Time'])
        currenddt = datetime.strptime(end_date+end_time, '%Y%m%d%H%M%S.%fZ')
        if 'end_datetime' not in metadata['top'].keys() or not metadata['top']['end_datetime'] or currenddt > metadata['top']['end_datetime']:
            metadata['top']['end_datetime'] = currenddt

        # These should be the same in all granule datasets...
        metadata['top']['source_name'] = assc(attrs_elem.attrs['Instrument_Short_Name']).lower()
        metadata['top']['platform_name'] = assc(fileobj.attrs['Platform_Short_Name']).lower()

        if 'MoonPhaseAngle' in data_elem:
            # Umm... Had to add [0] to make it work... Used to work ?? What changed ?
            # I added metadata['top'] to data files, but it doesn't work in geolocation file
            # reader either ?
            metadata['top']['moon_phase_angle'] = assc(data_elem['MoonPhaseAngle'].value[0])

    # Create dummy dataset with metadata if we specifically requested no channels
    if chans == []:
        # Will set up empty dataset in def read
        # Only need metadata['top'], everything else empty
        return 

    #Map SciFile geolocation variable names to names from the data file
    varmap = {'Latitude':   'Latitude',
              'Longitude':  'Longitude',
              'SatAzimuth': 'SatelliteAzimuthAngle',
              'SatZenith':  'SatelliteZenithAngle',
              'SunAzimuth': 'SolarAzimuthAngle',
              'SunZenith':  'SolarZenithAngle',
              'MoonAzimuth':'LunarAzimuthAngle',
              'MoonZenith': 'LunarZenithAngle',
             }
    #Use only terrain corrected data from DNB imagery
    if datasettag == 'DNB':
        varmap['Latitude'] = 'Latitude_TC'
        varmap['Longitude'] = 'Longitude_TC'

    # Previously we were not checking if we needed this particular 
    # resolution geolocation file (based on chans) before reading.
    if chans != None:
        needed_resolutions = []
        for chan in chans:
            if 'SVM' in chan:
                if 'MOD' not in needed_resolutions:
                    needed_resolutions += ['MOD']
            if 'SVI' in chan:
                if 'IMG' not in needed_resolutions:
                    needed_resolutions += ['IMG']
            if 'SVDNB' in chan:
                if 'DNB' not in needed_resolutions:
                    needed_resolutions += ['DNB']
            if 'NCC' in chan:
                if 'NCC' not in needed_resolutions:
                    needed_resolutions += ['NCC']

        if datasettag not in needed_resolutions:
            log.info('Resolution '+datasettag+' not required, SKIPPING')
            return 
        log.info('        Reading resolution '+datasettag)

    if datasettag not in gvars.keys():
        gvars[datasettag] = {}

    for ds_var, f_var in varmap.items():
        if f_var not in data_elem:
            continue
        if data_elem[f_var].dtype in (np.float32, np.dtype('>f4')):
            # MLS 20151207 There appear to be badvals besides just -999.7
            # at least for zenith angles ?
            badval = -900
            #badval = -999.7
        elif data_elem[f_var].dtype in (np.uint16, np.dtype('>u2')):
            badval = 65533
        else:
            raise SciFileError('Unexpected data type.  Unable to determine badval.')
        #data = np.ma.masked_equal(np.ma.array(data_elem[f_var].value), badval)
        data = np.ma.masked_less(np.ma.array(data_elem[f_var].value), badval)
        gvars[datasettag][ds_var] = data

    return 

def read_data_file(fileobj,gvars,datavars,metadata,chans=None):
    #Get attributes required for reading
    dat_prod = fileobj['Data_Products'].keys()[0]
    attrs_elem = fileobj['Data_Products'][dat_prod]
    short_name = assc(attrs_elem.attrs['N_Collection_Short_Name'])
    channel = short_name.split('-')[1]

    #Make sure the channel number is padded with zeros to two digits
    #So, I1 becomes I01
    if channel[1].isdigit():
        channel = '%s%02i' % (channel[0], int(channel[1:]))

    #Determine the resolution from the channel name
    if channel[0] == 'I':
        datasettag = 'IMG'
    elif channel[0] == 'M':
        datasettag = 'MOD'
    elif channel == 'DNB':
        datasettag = 'DNB'
    elif channel == 'NCC':
        datasettag = 'NCC'
    else:
        raise SciFileError('Unrecognized channel name encountered: %s' % channel)

    #Get data and time elements
    data_elem = fileobj['All_Data'][short_name+'_All']

    # When granules are packaged together (ie, Class), we can't just 
    # go by Gran_0, only gives us time range for one granule, not all.
    # Need to look at all granules to get full time range.
    for gran_name in attrs_elem.keys():
        # Each granule's dataset is named such as VIIRS-DNB-GEO_Gran_0, VIIRS-DNB-GEO_Gran_1
        #   etc. Need to get full time range based on those, not just Gran_0 (which worked
        #   fine for our near real time data - not so much for CLASS which packages multiple
        #   granules together)

        # We do not want to use the _Aggr dataset - it only has instrument name,
        # etc. No start/end datetime
        if "Gran_" not in gran_name:
            continue
        time_elem = attrs_elem[gran_name]

        #Get time attributes. Need to get min startdt / max enddt from ALL granules
        start_date = assc(time_elem.attrs['Beginning_Date'])
        start_time = assc(time_elem.attrs['Beginning_Time'])
        currstartdt = datetime.strptime(start_date+start_time, '%Y%m%d%H%M%S.%fZ')
        if 'start_datetime' not in metadata['top'].keys() or not metadata['top']['start_datetime'] or currstartdt < metadata['top']['start_datetime']:
            metadata['top']['start_datetime'] = currstartdt

        end_date = assc(time_elem.attrs['Ending_Date'])
        end_time = assc(time_elem.attrs['Ending_Time'])
        currenddt = datetime.strptime(end_date+end_time, '%Y%m%d%H%M%S.%fZ')
        if 'end_datetime' not in metadata['top'].keys() or not metadata['top']['end_datetime'] or currenddt > metadata['top']['end_datetime']:
            metadata['top']['end_datetime'] = currenddt

        # These should be the same in all granule datasets...
        metadata['top']['source_name'] = assc(attrs_elem.attrs['Instrument_Short_Name']).lower()
        metadata['top']['platform_name'] = assc(fileobj.attrs['Platform_Short_Name']).lower()
        metadata['top']['interpolation_radius_of_influence'] = 4500

        if 'MoonPhaseAngle' in data_elem:
            # Umm... Had to add [0] to make it work... Used to work ?? What changed ?
            # I added metadata['top'] to data files, but it doesn't work in geolocation file
            # reader either ?
            metadata['top']['moon_phase_angle'] = assc(data_elem['MoonPhaseAngle'].value[0])

    # Create dummy dataset with metadata if we explicitly requested NO channels
    if chans == []:
        return 

    #Map SciFile geolocation variable names to names from the data file
    varmap = {'SV%sRad': 'Radiance',
              'SV%sRef': 'Reflectance',
              'SV%sBT':  'BrightnessTemperature',
              'SV%sAlb': 'Albedo',
             }

    if datasettag not in datavars.keys():
        datavars[datasettag] = {}

    for ds_var, f_var in varmap.items():
        if chans != None and ds_var%channel not in chans:
            #log.info('        Did not request channel '+ds_var%channel+' SKIPPING')
            continue
        #Add the channel name to ds_var
        #shell()
        if f_var not in data_elem:
            # Check if something else is in data_elem
            for geoips_varname,h5varname in varmap.items():
                if h5varname in data_elem:
                    log.info(f_var+' was not in h5 file, but '+h5varname+' was, using '+h5varname)
                    f_var = h5varname
                    ds_var = geoips_varname
        if f_var not in data_elem:
            continue
        log.info('        Reading channel '+ds_var%channel)
        #Determine the badval
        if data_elem[f_var].dtype in (np.float32, np.dtype('>f4')):
            badval = -999.7
        elif data_elem[f_var].dtype in (np.uint16, np.dtype('>u2')):
            badval = 65533
        else:
            raise SciFileError('Unexpected data type.  Unable to determine badval.')
        #Read the actual data and mask it
        data = np.ma.masked_equal(np.ma.array(data_elem[f_var].value, dtype=np.float32), badval)

        #If scale and offset exist for the variable, read and apply them
        if f_var+'Factors' in data_elem:
            factors = data_elem[f_var+'Factors']
            data *= factors[0]
            data += factors[1]
        if 'NCC' == channel:
            data = np.ma.masked_greater(data, 900)
        datavars[datasettag][ds_var % channel] = data

    #Create the dataset
    return 

# For now must include this string for automated importing of classes.
reader_class_name = 'VIIRS_HDF5_Reader'
class VIIRS_HDF5_Reader(Reader):
    '''
    Give path examples here for a representative variable.
    '''
    dataset_info = {}

    @staticmethod
    def format_test(fname):
        # This reader only handles individual files, not multiple files or directories.
        # Change def read and def format_test if you want to handle directories directly.
        if os.path.isdir(fname):
            return False

        # Check that this file is hdf5 first
        from ..file_format_tests import hdf5_format_test
        if not hdf5_format_test(fname):
            return False

        fileobj = h5py.File(str(fname), mode='r')
        if not 'Mission_Name' in fileobj.attrs.keys():
            return False
        # Mission_Name used to be NPP, now S-NPP/JPSS
        if 'NPP' not in fileobj.attrs['Mission_Name'][0,0]:
            return False
        # This is VIIRS
        if not fileobj['Data_Products'].values()[0].attrs['Instrument_Short_Name'][0,0]:
            return False
        fileobj.close()
        return True

    def read(self,fname,datavars,gvars,metadata,chans=None,sector_definition=None):
        fileobj = h5py.File(str(fname), mode='r')
        #Currently have never seen a compositied file, so assuming only one channel per file
        if len(fileobj['Data_Products'].keys()) != 1:
            raise SciFileError('Assumption of one and only one group in Data_Products group failed.  Fix this.')
        dat_prod = fileobj['Data_Products'].keys()[0]
        # Sectoring doesn't work for very large sectors, but we can not always have sectoring turned off.
        # We would be processing too much data for every small sector.
        #metadata['top']['NON_SECTORABLE'] = True
  
        #Determine file type based on collection short name
        if fileobj['Data_Products'][dat_prod].attrs['N_Dataset_Type_Tag'] == 'GEO':
            read_geolocation_file(fileobj,gvars,datavars,metadata,chans=chans)
        elif fileobj['Data_Products'][dat_prod].attrs['N_Dataset_Type_Tag'] in ['SDR', 'EDR']:
            read_data_file(fileobj,gvars,datavars,metadata,chans=chans)
        else:
            log.warning('Unknown file type (not GEO, SDR, or EDR), skipping')


        if 'DNB' in datavars.keys() and 'DNB' in gvars.keys() and 'SVDNBRad' in datavars['DNB'].keys() and 'SVDNBRef' not in datavars['DNB'].keys():
            if chans and 'SVDNBRef' in chans:
                log.info('    Calculating Lunar Reflectances')
                try: 
                    from geoalgs import lunarref
                    datavars['DNB']['SVDNBRef'] = np.ma.masked_array(lunarref(datavars['DNB']['SVDNBRad'],
                                    gvars['DNB']['SunZenith'],
                                    gvars['DNB']['MoonZenith'],
                                    metadata['top']['start_datetime'].strftime('%Y%m%d%H'),
                                    metadata['top']['start_datetime'].strftime('%M'),
                                    metadata['top']['moon_phase_angle'],
                                    ))
                except: print 'Failed lunarref import in viirs_rdr2sdr.py.  If you need it, build it'
        return 

