# Python Standard Libraries
import os
from datetime import datetime

# Installed Libraries
try: import netCDF4 as ncdf
except: print 'Failed import netCDF4 in scifile/readers/winds_text_reader.py. If you need it, install it.'
import numpy as np
from scipy.interpolate import griddata
import logging


# GeoIPS Libraries
from .reader import Reader
from ..containers import DataSet,Variable,_empty_varinfo
from geoips.utils.path.datafilename import DataFileName

log = logging.getLogger(__name__)

dsdictkey = 'ds'
#dsdictkey = 'datasets'

channel_dict = { 
                'GOES15' : {
                            'satellite': 'himawari8',
                            'sensor': 'ahi',
                            'WV'  : 'B08BT', # 6.2um, Upper-level tropospheric Water Vapor band, IR
                            'WV10'  : 'B08BT', # 6.2um, Upper-level tropospheric Water Vapor band, IR
                            'WV11'  : 'B08BT', # 6.2um, Upper-level tropospheric Water Vapor band, IR
                            'WVCA'  : 'B08BT', # 6.2um, Upper-level tropospheric Water Vapor band, IR
                            'WVCT'  : 'B10BT', # 7.3um, Lower-level tropospheric Water Vapor band, IR
                            'VIS'   : 'B04Ref', # 1.37um, Cirrus band, near-IR 
                            'IR'    : 'B11BT', # 8.4um, Cloud-Top Phase band, IR
                            'SWIR'  : 'B07BT', # 3.9um, Shortwave window band, IR (with reflected daytime component)
                           },
                'GOES16' : {
                            'satellite': 'goes16',
                            'sensor': 'abi',
                            'WVCA'  : 'B08BT', # 6.2um, Upper-level tropospheric Water Vapor band, IR
                            'WVCT'  : 'B10BT', # 7.3um, Lower-level tropospheric Water Vapor band, IR
                            'VIS'   : 'B04Ref', # 1.37um, Cirrus band, near-IR 
                            'IR'    : 'B11BT', # 8.4um, Cloud-Top Phase band, IR
                            'SWIR'  : 'B07BT', # 3.9um, Shortwave window band, IR (with reflected daytime component)
                           },
                'HMWR08' : {
                            'satellite': 'himawari8',
                            'sensor': 'ahi',
                            'WVCA'  : 'B08BT', # 6.2um, Upper-level tropospheric Water Vapor band, IR
                            'WVCT'  : 'B10BT', # 7.3um, Lower-level tropospheric Water Vapor band, IR
                            'VIS'   : 'B04Ref', # 1.37um, Cirrus band, near-IR 
                            'IR'    : 'B11BT', # 8.4um, Cloud-Top Phase band, IR
                            'SWIR'  : 'B07BT', # 3.9um, Shortwave window band, IR (with reflected daytime component)
                           },
                'MET11' : {
                            'satellite': 'meteoEU',
                            'sensor': 'seviri',
                            'WV'  : 'B05BT', # WV_062 6.2um, Upper-level tropospheric Water Vapor band, IR
                            'WVCA'  : 'B05BT', # WV_062 6.2um, Upper-level tropospheric Water Vapor band, IR
                            'WVCT'  : 'B06BT', # WV_073
                            'VIS'   : 'B02Ref', # VIS008
                            'IR'    : 'B09BT', # IR_108
                            'SWIR'  : 'B04BT', # IR_039 3.9um, Shortwave window band, IR (with reflected daytime component)
                           },
                'MET8' : {
                            'satellite': 'meteoIO',
                            'sensor': 'seviri',
                            'WV'  : 'B05BT', # WV_062 6.2um, Upper-level tropospheric Water Vapor band, IR
                            'WVCA'  : 'B05BT', # WV_062 6.2um, Upper-level tropospheric Water Vapor band, IR
                            'WVCT'  : 'B06BT', # WV_073
                            'VIS'   : 'B02Ref', # VIS008
                            'IR'    : 'B09BT', # IR_108
                            'SWIR'  : 'B04BT', # IR_039 3.9um, Shortwave window band, IR (with reflected daytime component)
                           },
                'meteoIO' : {
                            'satellite': 'meteoIO',
                            'sensor': 'seviri',
                            'B04BT'  : 'B04BT', 
                            'B05BT'  : 'B05BT', 
                            'B06BT'  : 'B06BT', 
                            'B07BT'  : 'B07BT', 
                            'B08BT'  : 'B08BT', 
                            'B09BT'  : 'B09BT', 
                            'B10BT'  : 'B10BT', 
                            'B11BT'  : 'B11BT', 
                           },
                'meteoEU' : {
                            'satellite': 'meteoEU',
                            'sensor': 'seviri',
                            'B01Ref'  : 'B01Ref', 
                            'B02Ref'  : 'B02Ref', 
                            'B03Ref'  : 'B03Ref', 
                            'B04BT'  : 'B04BT', 
                            'B05BT'  : 'B05BT', 
                            'B06BT'  : 'B06BT', 
                            'B07BT'  : 'B07BT', 
                            'B08BT'  : 'B08BT', 
                            'B09BT'  : 'B09BT', 
                            'B10BT'  : 'B10BT', 
                            'B11BT'  : 'B11BT', 
                           },
                }

dataprovider_sat_dict = {
				'NOAA_Winds' : ['MET8','MET11','HMWR08','GOES16'],
				'Optical_Flow_Winds' : ['meteoIO','meteoEU'],
			}

# For now must include this string for automated importing of classes.
reader_class_name = 'Winds_Text_Reader'
class Winds_Text_Reader(Reader):

    @staticmethod
    def format_test(fname):
        # This reader only handles individual files, not multiple files or directories.
        # Change def read and def format_test if you want to handle directories.
        if os.path.isdir(fname):
            return False

        # Check that this file is text first
        from ..file_format_tests import ascii_format_test
        if not ascii_format_test(fname):
            return False

        with open(fname) as f:
            for linenum in range(0,20):
                line = f.readline()
                if 'lat' in line and 'lon' in line and 'spd' in line and 'dir' in line:
                    return True
        return False


    @staticmethod
    def get_empty_datfields():
        return {'typs'     : [],
               'sats'     : [],
               'days'     : [],
               'hms'      : [],
               'lats'     : [],
               'lons'     : [],
               'pres'     : [],
               'speed'     : [],
               'direction'      : [],
               'rffs'     : [],
               'qis'      : [],
               'intervs'  : [],
             }

    def read(self,fname,datavars,gvars,metadata,chans=None,sector_definition=None):
        '''
         type   sat      day     hms     lat     lon     pre   spd   dir   rff    qi  int
        WVCT   GOES16  20180312  1100   40.04    82.25   325   17.9  234  67.56  0.84   5
        WVCT   GOES16  20180312  1100   40.03    81.90   325   26.6  229  53.07  0.99   5
        WVCT   GOES16  20180312  1100   40.06    81.75   325   25.5  224  60.47  1.00   5
        '''

        '''
        Grab necessary metadata that will populate the _finfo, 
        _dsinfo, and _varinfo properties on the SciFile object.
        These get passed along when initializing the Variable 
        instance, then get propagated up to the dsinfo and finfo
        levels.
        The available fields for varinfo can be found in 
        scifile/containers.py at the beginning of the file.
        '''
        metadata['top']['platform_name'] = 'windvectors'
        metadata['top']['source_name'] = 'winds'
        metadata['top']['dataprovider'] = None
        metadata['top']['NON_SECTORABLE'] = True
        metadata['top']['NO_GRANULE_COMPOSITES'] = True

        metadata['top']['start_datetime'] = None

        dat = {}

        with open(fname) as fp:
            while not metadata['top']['start_datetime']:
                parts = fp.readline().split()
                if 'CLASSIFICATION:' in parts:
                    metadata['top']['classification'] = parts[-1]
                    continue
                if len(parts) == 12:
                    typ,sat,day,hms,lat,lon,pre,spd,dr,rff,qi,interv = parts
                elif len(parts) == 11:
                    typ,sat,day,hms,lat,lon,pre,spd,dr,rff,qi = parts
                    interv = 0
                elif len(parts) == 9:
                    typ,sat,day,hms,lat,lon,pre,spd,dr = parts
                    interv = 0
                    rff = 0
                    qi = 0
                else:
                    log.info('Skipping header line %s'%(parts))
                    continue
                interv = 0
                try:
                    metadata['top']['start_datetime'] = datetime.strptime(day+hms,'%Y%m%d%H%M')
                    metadata['top']['end_datetime'] = metadata['top']['start_datetime']
                    metadata['top']['filename_datetime'] = metadata['top']['start_datetime']
                    for dataprovider in dataprovider_sat_dict.keys():
						if sat in dataprovider_sat_dict[dataprovider]:
							metadata['top']['dataprovider'] = dataprovider
                    if chans == []:
                        '''
                        chans == [] specifies we don't want to read ANY data, just metadata.
                        chans == None specifies that we are not specifying a channel list, 
                                       and thus want ALL channels.
                        If NO CHANNELS were specifically requested, just return at this 
                        point with the metadata fields populated. A dummy SciFile dataset 
                        will be created with only metadata. This is for checking what 
                        platform/source combination we are using, etc.
                        '''
                        return
                except ValueError:
                    continue
            for cnt,line in enumerate(fp):
                parts = line.split()
                if len(parts) == 12:
                    typ,sat,day,hms,lat,lon,pre,spd,dr,rff,qi,interv = parts
                elif len(parts) == 11:
                    typ,sat,day,hms,lat,lon,pre,spd,dr,rff,qi = parts
                    interv = 0
                elif len(parts) == 9:
                    typ,sat,day,hms,lat,lon,pre,spd,dr = parts
                    interv = 0
                    rff = 0
                    qi = 0
                else:
                    log.error('Unsupported format for %s'%(parts))
                pre = int(pre)
                keyall = "{}_{}_All_Pressure_Levels".format(sat,typ)
                #if pre >= 0 and pre <= 400: # High
                #    key = '%s_%s_%s'%(sat,typ,'0_to_399_mb')
                #elif pre >= 400 and pre <= 800: # Medium
                #    key = '%s_%s_%s'%(sat,typ,'400_to_799_mb')
                #elif pre >= 800: # Low
                #    key = '%s_%s_%s'%(sat,typ,'800_to_1014_mb')
                #else:
                #    log.warning('Pressure outside allowable range: '+str(pre))
                #    continue
                #if key not in dat.keys():
                #    log.info('Starting dataset %s'%(key))
                #    dat[key] = self.get_empty_datfields()
                #    datavars[key] = {}
                #    metadata['top']['alg_platform'] = channel_dict[sat]['satellite']
                #    metadata['top']['alg_source'] = channel_dict[sat]['sensor']
                #    metadata[dsdictkey][key] = {}
                if keyall not in dat.keys():
                    log.info('Starting dataset %s'%(keyall))
                    dat[keyall] = self.get_empty_datfields()
                    datavars[keyall] = {}
                    metadata['top']['alg_platform'] = channel_dict[sat]['satellite']
                    metadata['top']['alg_source'] = channel_dict[sat]['sensor']
                    metadata[dsdictkey][keyall] = {}
                #dat[key]['days'] += [day]
                #dat[key]['hms']+= [hms]
                #dat[key]['lats'] += [lat]
                #dat[key]['lons'] += [lon]
                #dat[key]['pres'] += [pre]
                #dat[key]['speed'] += [spd]
                #dat[key]['direction']+= [dr]
                #dat[key]['rffs'] += [rff]
                #dat[key]['qis']+= [qi]
                #dat[key]['intervs'] += [interv]

                dat[keyall]['days'] += [day]
                dat[keyall]['hms']+= [hms]
                dat[keyall]['lats'] += [lat]
                dat[keyall]['lons'] += [lon]
                dat[keyall]['pres'] += [pre]
                dat[keyall]['speed'] += [spd]
                dat[keyall]['direction']+= [dr]
                dat[keyall]['rffs'] += [rff]
                dat[keyall]['qis']+= [qi]
                dat[keyall]['intervs'] += [interv]

                #metadata[dsdictkey][key]['alg_platform'] = channel_dict[sat]['satellite']
                #metadata[dsdictkey][key]['alg_wavelength'] = typ
                #metadata[dsdictkey][key]['alg_channel'] = channel_dict[sat][typ]

                metadata[dsdictkey][keyall]['alg_platform'] = channel_dict[sat]['satellite']
                metadata[dsdictkey][keyall]['alg_wavelength'] = typ
                metadata[dsdictkey][keyall]['alg_channel'] = channel_dict[sat][typ]


        minlat = 999
        minlon = 999
        maxlat = -999
        maxlon = -999
        for typ in dat.keys():
            for key,arr in dat[typ].items():
                if key == 'lats':
                    datavars[typ]['lats'] = np.array(map(float, arr))
                    if datavars[typ]['lats'].min() < minlat:
                        minlat = datavars[typ]['lats'].min()
                    if datavars[typ]['lats'].max() > maxlat:
                        maxlat = datavars[typ]['lats'].max()
                elif key == 'lons':
                    if sat == 'HMWR8' or sat == 'GOES16' or sat == 'MET8' or sat == 'MET11' or sat == 'GOES15':
                        # CIMSS STORES LONS OPPOSITE!!!!!
                        datavars[typ][key] = -1.0 * np.array(map(float, arr))
                    else:
                        datavars[typ][key] = 1.0 * np.array(map(float, arr))

                    # Crosses dateline
                    if abs(datavars[typ][key].min()) > 179 and abs(datavars[typ][key].max()) > 179:
                        currminlon = np.extract(datavars[typ][key]>0,datavars[typ][key]).min()
                    else:
                        currminlon = datavars[typ][key].min()

                    if currminlon < minlon:
                        minlon = datavars[typ][key].min()
                    if datavars[typ][key].max() > maxlon:
                        maxlon = datavars[typ][key].max()
                elif key == 'speed':
                    # Stored as m/s by default, convert to ms for specific data types if needed.
                    datavars[typ]['speed_ms'] = np.array(map(float, arr))
                elif key == 'direction':
                    # Stored as degrees by default, convert to deg for specific data types if needed.
                    datavars[typ]['direction_deg'] = np.array(map(float, arr))
                elif key == 'pres':
                    # Stored as mb by defauts, convert to mb for specific data types if needed.
                    datavars[typ]['pres_mb'] = np.array(map(float, arr))
                elif key in ['rffs','qis','intervs']:
                    try:
                        datavars[typ][key] = np.array(map(float, arr))
                    except ValueError as resp:
                        log.warning("{} Poorly formatted, skipping line for {} {} ".format(resp, key, typ)) 
                elif key in ['days','hms']:
                    datavars[typ][key] = np.array(map(int, arr)) 

        #nx,ny = (500,500)
        #x = np.linspace(minlon, maxlon, nx)
        #y = np.linspace(maxlat, minlat, ny)
        #gridlons,gridlats = np.meshgrid(x,y)

        #for typ in datavars.keys():
        #    dsname = typ.replace('1d','grid')
        #    if datavars[typ]['speed'].size >= 4:
        #        log.info('Interpolating data to grid for %s, %d points'%(dsname,datavars[typ]['speed'].size))
        #    else:
        #        log.info('Not enough points to interpolate data to grid for %s, %d points'%(dsname,datavars[typ]['speed'].size))
        #        continue

        #    speed = datavars[typ]['speed']
        #    direction = datavars[typ]['direction']
        #    lats = datavars[typ]['lats']
        #    lons = datavars[typ]['lons']
        #    pres = datavars[typ]['pres']
        #    u = (speed * np.cos(np.radians(direction)))#*1.94384
        #    v = (speed * np.sin(np.radians(direction)))#*1.94384

        #    # interpolate
        #    gridpres = np.ma.masked_invalid(griddata((lats,lons),pres,(gridlats,gridlons),method='linear'))
        #    gridu = np.ma.masked_invalid(griddata((lats,lons),u,(gridlats,gridlons),method='linear'))
        #    gridv = np.ma.masked_invalid(griddata((lats,lons),v,(gridlats,gridlons),method='linear'))
        #    gridspeed = np.ma.masked_invalid(griddata((lats,lons),speed,(gridlats,gridlons),method='linear'))
        #    gvars[dsname] = {}
        #    datavars[dsname] = {}
        #    datavars[dsname]['gridpres'] = np.ma.masked_invalid(gridpres)
        #    datavars[dsname]['gridu'] = np.ma.masked_invalid(gridu)
        #    datavars[dsname]['gridv'] = np.ma.masked_invalid(gridv)
        #    datavars[dsname]['gridspeed'] = np.ma.masked_invalid(gridspeed)

        #    gvars[dsname]['Latitude'] = gridlats
        #    gvars[dsname]['Longitude'] = gridlons
        #    clat= 30
        #    clon = 10
        #    gridinds = np.where((gridlons>clon) & (gridlons<clon+1) & (gridlats>clat) & (gridlats<clat+1))
        #    inds = np.where((lons>clon) & (lons<clon+1) & (lats>clat) & (lats<clat+1))

        #        
        ## datavars, gvars, and metadata are passed by reference, so we do not have to return anything.
