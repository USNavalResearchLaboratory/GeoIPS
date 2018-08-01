# Python Standard Libraries
import logging
import os
from datetime import datetime


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
reader_class_name = 'MODEL_GRIB_Reader'
class MODEL_GRIB_Reader(Reader):

    dataset_info = { #'TIME': {'time': 'validityTime'},
                     'DATA': {'temp':'Temperature',
                              'uwind':'U component of wind',
                              'vwind':'V component of wind',
                              'cmr':'Cloud mixing ratio',
                              'cloudcov': 'Total Cloud Cover',
                              'icecov': 'Ice cover (1=ice, 0=no ice)',
                              'snowdepth': 'Snow depth',
                              'dp':'Dew point depression (or deficit)',
                              'geoph':'Geopotential Height',
                              'rh':'Relative humidity',
                              'av':'Absolute vorticity',
                              'vpress':'Vapour pressure',
                              'vv':'Vertical velocity',
                              'lwrf': 'Long wave radiation flux',
                              'swrf': 'Net short-wave radiation flux (surface)',
                              'ltnt_heat_flux':'Latent heat flux',
                              'snsb_heat_flux':'Sensible heat flux',
                              'wnd_strs_ucmp':'Momentum flux, u-component',
                              'wnd_strs_vcmp':'Momentum flux, v-component',
                              'pres_msl':'Mean sea level pressure',
                              'pres':'Pressure',
                              'surfpres': 'Surface pressure',
                              'ttl_prcp':'Total Precipitation',
                              'wt':'Water temperature',
                              '10mvwind':'10 metre V wind component',
                              '10muwind':'10 metre U wind component',
                              'slp':'Mean sea level pressure',
                              'mfv':'Momentum flux, v-component',
                              'mfu':'Momentum flux, u-component',
                              'lhf':'Latent heat flux',
                              'precip':'Total Precipitation',
                              'shf':'Sensible heat flux',
                              'num238':'238 (instant)',
                              'num133':'133 (instant)',
                              'num222':'222 (instant)',
                              'num221':'221 (instant)',
                              'num218':'218 (instant)',
                            },
                   }
    gvar_info = { 'DATA': {
                         'Latitude': 'latitudes',
                         'Longitude': 'longitudes',
                        },
                }

    @staticmethod
    def format_test(fname):
        # This reader only handles individual files, not multiple files or directories.
        # Change def read and def format_test if you want to handle directories directly.
        if os.path.isdir(fname):
            return False

        # Check that this file is grib first
        from ..file_format_tests import grib_format_test
        if not grib_format_test(fname):
            return False
        
        df = pg.open(fname)
        temp = None
        for vars in MODEL_GRIB_Reader.dataset_info.values():
            for var in vars.values():
                try:
                    temp= df.select(name = var)[0]
                except:
                    # The 238 / 133 ones don't work with name=var...
                    if var == '238 (instant)' or var == '133 (instant)' or var == '222 (instant)' or var == '218 (instant)' or var == '221 (instant)':
                        temptemp = df.select()
                        if var in str(temptemp):
                            temp = temptemp[0]
                    continue
        #temp = df.select(name = 'Temperature')[0]

        #if not temp:
        #    return True
        if hasattr(temp,'centre') and temp.centre == 'fnmo':
            return True
        elif hasattr(temp,'centre') and temp.centre == 'kwbc':
            return True
        elif hasattr(temp,'valid_key') and temp.valid_key('centre') and temp['centre'] == 'fnmo':
            return True
        return False

    def read(self,fname,datavars,gvars,metadata,chans=None,sector_definition=None):
        # Since the variables are all contained within separate files, we need to allow for 
        # a loop to cycle through the files
        df = pg.open(fname)
        temp = None
        for vars in MODEL_GRIB_Reader.dataset_info.values():
            for var in vars.values():
                try:
                    temp= df.select(name = var)[0]#grabs the first file
                except:
                    if var == '238 (instant)' or var == '133 (instant)' or var == '222 (instant)' or var == '218 (instant)' or var == '221 (instant)':
                        temptemp = df.select()
                        if var in str(temptemp):
                            temp = temptemp[0]
                    continue
        #temp = df.select(name = 'Temperature')[0]
        
        #print 'Entering IPython shell in '+self.name+' for development purposes'
        #shell()
        dt='{:08d}{:04d}'.format(temp.validityDate, temp.validityTime)
        print dt

        if not temp:
            log.warning('Unable to read from file '+fname+' no matching select for vars')
            return 
        if temp.validityDate:
            metadata['top']['start_datetime'] = datetime.strptime(dt,'%Y%m%d%H%M')
            metadata['top']['end_datetime'] = datetime.strptime(dt,'%Y%m%d%H%M')
        else:
            metadata['top']['start_datetime'] = temp.analDate
            metadata['top']['end_datetime'] = temp.analDate
        metadata['top']['dataprovider'] = temp.centre
        metadata['top']['filename_datetime'] = metadata['top']['start_datetime']
        metadata['top']['platform_name'] = 'model'
        #metadata['top']['source_name'] = 'model'
        metadata['top']['tau'] = temp.startStep
        metadata['top']['level'] = temp.level
        
        if 'COAMPS' in fname:
            metadata['top']['source_name'] = 'coamps'
        else:
            metadata['top']['source_name'] = 'navgem'

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

        new = None
        # Loop through each dataset name found in the dataset_info property above.
        for dsname in self.dataset_info.keys():
            for geoipsvarname,dfvarname in self.dataset_info[dsname].items():
                try:
                    new= df.select(name=dfvarname)#,typeOfLevel='isobaricInhPa')
                except:
                    continue
                for newest in new:
                    newest
                    data = newest.values
                    fillvalue = newest.missingValue
                    level = newest.level
                    #shell()
                    if newest.units == str('m s**-1'):
                        data = data*1.94384
                    
                    log.info('    Reading '+dsname+' channel "'+dfvarname +
                             '" from file into SciFile channel: "' +
                             geoipsvarname+str(level)+'" ...')
                    datavars[dsname][geoipsvarname+str(level)] = np.ma.masked_equal(data,fillvalue)
                    shape = datavars[dsname][geoipsvarname+str(level)].shape
        if not new:
            log.warning('Unable to read from file '+fname+' no matching select for isobarikcInhPa for var '+str(dfvarname))
            return
        # Loop through each dataset name found in the gvar_info property above.
        for dsname in self.gvar_info.keys():
            for geoipsvarname,dfvarname in self.gvar_info[dsname].items():
                log.info('    Reading '+dsname+' channel "'+dfvarname+'" from file into SciFile channel: "'+geoipsvarname+'"...')
                for newest in new:
                    newest
                data = newest[dfvarname]
                fillvalue = newest.missingValue
                #shell() 
                if data.size == newest.getNumberOfValues:
                    data = np.reshape(data,shape)
                #if data.shape == (1038240,):
                #    data= np.reshape(data,(721,1440))
                #elif data.shape == (259920,):
                #    data= np.reshape(data,(361,720))
                #elif data.shape == (76454,):
                #    data= np.reshape(data,(254, 301))
                gvars[dsname][geoipsvarname] = np.ma.masked_equal(data,fillvalue)
