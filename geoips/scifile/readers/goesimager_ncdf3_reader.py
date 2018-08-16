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
from datetime import datetime,timedelta
import os
from glob import glob


# Installed Libraries
import numpy as np
try: import netCDF4 as ncdf
except: print 'Failed import netCDF4 in scifile/readers/goesimager_ncdf3_reader.py. If you need it, install it.'
# from scipy.ndimage.interpolation import map_coordinates
from IPython import embed as shell


# GeoIPS Libraries
from .reader import Reader
from ..satnav import satnav
from ..scifileexceptions import SciFileError
from ..containers import _empty_varinfo, _empty_dsinfo, Variable, DataSet
from geoips.utils.satellite_info import all_sats_for_sensor,SatSensorInfo
from geoips.utils.log_setup import interactive_log_setup

log = interactive_log_setup(logging.getLogger(__name__))

def create_reflectance(var):
    '''Coefficients gathered from www.ospo.noaa.gov/Operations/GOES/calibration/goes-vis-ch-calibration.html'''
    vis_coefficients = {'G-10':{'m': 0.558,
                                   'b': -16.18,
                                   'k': 1.98808e-3,
                                  },
                        'G-11':{'m': 0.556,
                                   'b': -16.12,
                                   'k': 2.01524e-3,
                                  },
                        'G-12':{'m': 0.577,
                                   'b': -16.72,
                                   'k': 1.97658e-3,
                                  },
                        'G-13':{'m': 0.610,
                                   'b': -17.70,
                                   'k': 1.89544e-3,
                                  },
                        'G-14':{'m': 0.586,
                                   'b': -17.00,
                                   'k': 1.88772e-3,
                                  },
                        'G-15':{'m': 0.585,
                                   'b': -16.98,
                                   'k': 1.88852e-3,
                                  },
                       }
    coeff = vis_coefficients[var.platform_name]
    m = coeff['m']
    b = coeff['b']
    k = coeff['k']
    ref = 100.0*k*(m*(var/32.0)+b)
    return ref

def create_brightness_temperature(var):
    '''Coefficients gathered from www.ospo.noaa.gov/Operations/GOES/calibration/gvar-conversion.html'''
    ir_coefficients = {'G-10':{'gvar_ch2':{'m':227.3889,
                                              'b':68.2167,
                                              'n':2552.9845,
                                              'a':-0.60584483,
                                              'b2':1.0011017,
                                             },
                                  'gvar_ch3':{'m':38.8383,
                                              'b':29.1287,
                                              'n':1486.2212,
                                              'a':-0.61653805,
                                              'b2':1.0014011,
                                             },
                                  'gvar_ch4':{'m':5.2285,
                                              'b':15.6854,
                                              'n':936.0, #Average of two numbers
                                              'a':-0.279000, #Average of two numbers
                                              'b2':1.0009680, #Average of two numbers
                                             },
                                  'gvar_ch5':{'m':5.0273,
                                              'b':15.3332,
                                              'n':830.890, #Average of two numbers
                                              'a':-0.2626, #Average of two numbers
                                              'b2':1.0009025, #Average of two numbers
                                             },
                                 },
                       'G-11':{'gvar_ch2':{'m':227.3889,
                                              'b':68.2167,
                                              'n':2562.07,
                                              'a':-0.644790,
                                              'b2':1.000775,
                                             },
                                  'gvar_ch3':{'m':38.8383,
                                              'b':29.1287,
                                              'n':1481.53,
                                              'a':-0.543401,
                                              'b2':1.001495,
                                             },
                                  'gvar_ch4':{'m':5.2285,
                                              'b':15.6854,
                                              'n':931.76,
                                              'a':-0.306809,
                                              'b2':1.001274,
                                             },
                                  'gvar_ch5':{'m':5.0273,
                                              'b':15.3332,
                                              'n':833.365, #Average of two numbers
                                              'a':-0.324163, #Average of two numbers
                                              'b2':1.001000, #Average of two numbers
                                             },
                                 },
                       'G-12':{'gvar_ch2':{'m':227.3889,
                                              'b':68.2167,
                                              'n':2562.45,
                                              'a':-0.650731,
                                              'b2':1.001520,
                                             },
                                  'gvar_ch3':{'m':38.8383,
                                              'b':29.1287,
                                              'n':1536.69,#Average of two numbers
                                              'a':-4.770222,#Average of two numbers
                                              'b2':1.012412,#Average of two numbers
                                             },
                                  'gvar_ch4':{'m':5.2285,
                                              'b':15.6854,
                                              'n':933.21,#Average of two numbers
                                              'a':-0.360250,#Average of two numbers
                                              'b2':11.001306,#Average of two numbers
                                             },
                                  'gvar_ch6':{'m':5.5297,
                                              'b':16.5892,
                                              'n':751.775,
                                              'a':-0.252130,
                                              'b2':1.000742,
                                             },
                                 },
                       'G-13':{'gvar_ch2':{'m':227.3889,
                                              'b':68.2167,
                                              'n':2561.74,
                                              'a':-1.437204,
                                              'b2':1.002562,
                                             },
                                  'gvar_ch3':{'m':38.8383,
                                              'b':29.1287,
                                              'n':1522.12,#Average of two numbers
                                              'a':-3.616752,#Average of two numbers
                                              'b2':1.010014,#Average of two numbers
                                             },
                                  'gvar_ch4':{'m':5.2285,
                                              'b':15.6854,
                                              'n':937.25,#Average of two numbers
                                              'a':-0.383576,#Average of two numbers
                                              'b2':1.001292,#Average of two numbers
                                             },
                                  'gvar_ch6':{'m':5.5297,
                                              'b':16.5892,
                                              'n':749.830,
                                              'a':-0.134801,
                                              'b2':1.000482,
                                             },
                                 },
                       'G-14':{'gvar_ch2':{'m':227.3889,
                                              'b':68.2167,
                                              'n':2577.98,
                                              'a':-1.596954,
                                              'b2':1.002631,
                                             },
                                  'gvar_ch3':{'m':38.8383,
                                              'b':29.1287,
                                              'n':1529.59,#Average of two numbers
                                              'a':-3.587800,#Average of two numbers
                                              'b2':1.009519,#Average of two numbers
                                             },
                                  'gvar_ch4':{'m':5.2285,
                                              'b':15.6854,
                                              'n':936.17,#Average of two numbers
                                              'a':-0.288700,#Average of two numbers
                                              'b2':1.001262,#Average of two numbers
                                             },
                                  'gvar_ch6':{'m':5.5297,
                                              'b':16.5892,
                                              'n':753.520,
                                              'a':-0.211737,
                                              'b2':1.000650,
                                             },
                                 },
                       'G-15':{'gvar_ch2':{'m':227.3889,
                                              'b':68.2167,
                                              'n':2563.7905,
                                              'a':-1.5693377,
                                              'b2':1.0025034,
                                             },
                                  'gvar_ch3':{'m':38.8383,
                                              'b':29.1287,
                                              'n':1521.1988, #Average of two numbers
                                              'a':-3.4706545,#Average of two numbers
                                              'b2':1.0093296,#Average of two numbers
                                             },
                                  'gvar_ch4':{'m':5.2285,
                                              'b':15.6854,
                                              'n':935.89417,#Average of two numbers
                                              'a':-0.36151367, #Average of two numbers
                                              'b2':1.0012715,#Average of two numbers
                                             },
                                  'gvar_ch6':{'m':5.5297,
                                              'b':16.5892,
                                              'n':753.72229,
                                              'a':-0.21475817,
                                              'b2':1.0006485,
                                             },
                                 },
                       }

    coeff = ir_coefficients[var.platform_name][var.name]

    m = coeff['m']
    b = coeff['b']
    n = coeff['n']
    a = coeff['a']
    b2 = coeff['b2']
    c1 = 1.191066e-5
    c2 = 1.438833

    rad = ((var/32.0)-b)/m
    Teff = (c2*n)/np.log(1+(c1*n**3)/rad)
    T = (a + b2*Teff)
    return T

# For now must include this string for automated importing of classes.
reader_class_name = 'GOESImager_TDFNC_Reader'
class GOESImager_TDFNC_Reader(Reader):
    dataset_info = { 'HIGH': ['gvar_ch1'],
                     'LOW' : ['gvar_ch2','gvar_ch3','gvar_ch4'],
                     'CO2' : ['gvar_ch6'],
                   }
    @staticmethod
    def format_test(fname):
        # This reader only handles individual files, not multiple files or directories.
        # Change def read and def format_test if you want to handle directories directly.
        if os.path.isdir(fname):
            return False

        # Check that this file is ncdf3 first
        from ..file_format_tests import ncdf3_format_test
        if not ncdf3_format_test(fname):
            return False

        try:
            fileobj = ncdf.Dataset(str(fname), 'r')
        except RuntimeError:
            return False
        try:
            satellite = fileobj.getncattr('satellite')
            sensor = fileobj.getncattr('sensor_name')
        except AttributeError:
            fileobj.close()
            return False
        if 'goes-' in satellite and sensor == 'gvissr':
            fileobj.close()
            return True

    def read(self,fname,datavars,gvars,metadata,chans=None,sector_definition=None):
        fileobj = ncdf.Dataset(str(fname), 'r')

        if chans and not (set(fileobj.variables.keys()) & set(chans)):
            log.info('Did not request any variables from '+fname+', only need '+str(chans)+', returning empty list')
            return 

        #Read the date and time
        # Terascan stores the "pass_date" as days since Jan 1 1900 (inclusive), and 
        # "start_time" as seconds since midnight.
        sdt = datetime.strptime('1899-12-31','%Y-%m-%d')+timedelta(days=int(fileobj.getncattr('pass_date')),seconds=float(fileobj.getncattr('start_time')))
        if not metadata['top']['start_datetime'] or sdt < metadata['top']['start_datetime']:
            metadata['top']['start_datetime'] = sdt

        satellite = fileobj.getncattr('satellite')
        for sat in all_sats_for_sensor('gvar'):
            si = SatSensorInfo(sat)
            if si.tscan_tle_name == satellite:
                metadata['top']['platform_name'] = si.geoips_satname
        # Terascan stores sensor as gvissr, we want to call it gvar.
        metadata['top']['source_name'] = 'gvar'
        metadata['top']['NO_GRANULE_COMPOSITES'] = True
        # Not sure why I added this.  
        metadata['top']['NON_SECTORABLE'] = True

        # Create dummy dataset with metadata if we specifically requested no channels
        if chans == []:
            # Will set up empty dataset in def read
            # Only need varinfo, everything else empty
            return 

        log.info('Reading '+fname+' Requested channels: '+str(chans))

        #Read the geolocation data in the native resolution from Terascan.
        log.info('    Reading longitudes...')
        lon = fileobj.variables['longitude'][...]

        log.info('    Reading latitudes...')
        lat = fileobj.variables['latitude'][...]

        log.info('    Reading solar zenith angles...')
        zen = fileobj.variables['sun_zenith'][...]

        # Find which dataset this channel should be in
        for dslabel in self.dataset_info.keys():
            if set(fileobj.variables.keys()) & set(self.dataset_info[dslabel]):
                datasettag = dslabel

        alldata = []
        #Read the actual data
        for chn in fileobj.variables.keys():
            if chans != None and chn not in chans:
                if chn not in ['latitude','longitude','sun_zenith']:
                    log.info('    Did not request variable '+chn+', skipping...')
                continue

            if 'Latitude' not in gvars[datasettag].keys():
                gvars[datasettag]['Latitude'] = lat
                gvars[datasettag]['Longitude'] = lon
                gvars[datasettag]['SunZenith'] = zen

            log.info('    Reading '+datasettag+' data: '+chn+'...')
            data = fileobj.variables[chn][...]
            if hasattr(data,'fill_value'):
                datavars[datasettag][chn] = data
            else:
                # I think if there are no masked values, tdfnc does not create a 
                # mask.  So this should work fine... Just nothing will get masked...
                if data.min() > -32768:
                    maskval = -32768
                else:
                    maskval = 100*data.min()
                datavars[datasettag][chn] = np.ma.masked_equal(data,maskval)
    

        fileobj.close()

        return 

    @staticmethod
    def create_reflectance(var):
        return create_reflectance(var)

    @staticmethod
    def create_brightness_temperature(var):
        return create_brightness_temperature(var)

class GOESImager_NCDF3_Reader(Reader):
    dataset_info = { 'CO2' : {'gvar_ch6':6}, 
                     'HIGH': {'gvar_ch1':1},
                     'LOW' : {'gvar_ch2':2,
                              'gvar_ch3':3,
                              'gvar_ch4':4},
                   }

    @staticmethod
    def format_test(fname):
        try:
            fileobj = ncdf.Dataset(str(fname), 'r')
        except RuntimeError:
            return False
        try:
            satellite, sensor = fileobj.getncattr('Satellite Sensor').split()
        except AttributeError:
            fileobj.close()
            return False
        if satellite in ['G-13', 'G-14', 'G-15'] and sensor == 'IMG':
            fileobj.close()
            return True

    def read(self,fname,gvars,datavars,metadata,chans=None,sector_definition=None):
        fileobj = ncdf.Dataset(str(fname), 'r')

        #Read the date and time
        date = '%07i' % fileobj.variables['imageDate'].getValue()
        time = '%06i' % fileobj.variables['imageTime'].getValue()

        sdt = datetime.strptime(date+time, '%Y%j%H%M%S')
        if not metadata['top']['start_datetime'] or sdt < metadata['top']['start_datetime']:
            metadata['top']['start_datetime'] = sdt

        satellite, sensor = fileobj.getncattr('Satellite Sensor').split()
        if satellite == 'g13':
            metadata['top']['platform_name'] = 'goesE'
        elif satellite == 'g15':
            metadata['top']['platform_name'] = 'goesW'
        else:
            metadata['top']['platform_name'] = satellite
        metadata['top']['source_name'] = 'gvar'

        # Create dummy dataset with metadata if we specifically requested no channels
        if chans == []:
            return 

        #Determine what bands we have in this file
        #Currently only one band per file.  Maybe different later?
        #When only one band per file, this is returned as a scalar
        band = fileobj.variables['bands'].getValue()


        #Read the actual data
        data = fileobj.variables['data'][...].squeeze()

        #Create the dataset
        # Keys are scifile variables, values are original datafile variables.
        for dslabel in self.dataset_info.keys():
            for currgeoipsvarname,ncbandnum in self.dataset_info[dslabel].items():
                if band == ncbandnum:
                    datasettag = dslabel
                    geoipsvarname = currgeoipsvarname
        if datasettag == 'HIGH':
            data = self.create_reflectance(data)
        elif datasettag == 'LOW':
            data = self.create_brightness_temperature(data)
        elif datasettag == 'CO2':
            data = self.create_brightness_temperature(data)
        elif band in [5]:
            raise SciFileError('This must be an OLD goes file with channel 5 included.  This case has not been handled.  Please edit goesimager_ncdf3_reader.py')
        else:
            raise SciFileError('Unrecognized band encountered: %s' % band)

        lon = np.ma.masked_equal(fileobj.variables['lon'][...], 2.1432893e9).squeeze()
        lat = np.ma.masked_equal(fileobj.variables['lat'][...], 2.1432893e9).squeeze()
        gvars[datasettag]['Longitude'] = lon
        gvars[datasettag]['Latitude'] = lat
        gvars[datasettag]['SunZenith'] = satnav('SunZenith', varinfo['start_datetime'], lon, lat)
        datavars[datasettag][geoipsvarname] = data

        return 

    @staticmethod
    def create_reflectance(var):
        return create_reflectance(var)

    @staticmethod
    def create_brightness_temperature(var):
        return create_brightness_temperature(var)


