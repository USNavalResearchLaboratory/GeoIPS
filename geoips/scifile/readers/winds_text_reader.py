# Python Standard Libraries
import os
from datetime import datetime

# Installed Libraries
from IPython import embed as shell
try: import netCDF4 as ncdf
except: print 'Failed import netCDF4 in scifile/readers/knmirscat_ncdf3_reader.py. If you need it, install it.'
import numpy as np
from scipy.interpolate import griddata
import logging


# GeoIPS Libraries
from .reader import Reader
from ..containers import DataSet,Variable,_empty_varinfo
from geoips.utils.path.datafilename import DataFileName

log = logging.getLogger(__name__)

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
        metadata['top']['source_name'] = 'dmv'
        metadata['top']['dataprovider'] = 'cimss'
        metadata['top']['NON_SECTORABLE'] = True
        metadata['top']['NO_GRANULE_COMPOSITES'] = True

        metadata['top']['start_datetime'] = None

        dat = {}

        with open(fname) as fp:
            while not metadata['top']['start_datetime']:
                try:
                    typ,sat,day,hms,lat,lon,pre,spd,dr,rff,qi,interv = fp.readline().split()
                except ValueError:
                    typ,sat,day,hms,lat,lon,pre,spd,dr,rff,qi = fp.readline().split()
                    interv = 0
                try:
                    metadata['top']['start_datetime'] = datetime.strptime(day+hms,'%Y%m%d%H%M')
                    metadata['top']['end_datetime'] = metadata['top']['start_datetime']
                    metadata['top']['filename_datetime'] = metadata['top']['start_datetime']
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
                try:
                    typ,sat,day,hm,lat,lon,pre,spd,dr,rff,qi,interv = line.split()
                except ValueError:
                    typ,sat,day,hm,lat,lon,pre,spd,dr,rff,qi = line.split()
                    interv = 0
                pre = int(pre)
                if pre >= 100 and pre < 250:
                    key = sat+typ+'100to2501d'
                elif pre >= 251 and pre < 350:
                    key = sat+typ+'251to3501d'
                elif pre >= 400 and pre < 599:
                    key = sat+typ+'400to5991d'
                elif pre >= 600 and pre < 799:
                    key = sat+typ+'600to7991d'
                elif pre >= 800 and pre <= 950:
                    key = sat+typ+'800to9501d'
                else:
                    log.warning('Pressure outside allowable range: '+str(pre))
                    continue
                if key not in dat.keys():
                    dat[key] = self.get_empty_datfields()
                    datavars[key] = {}
                dat[key]['days'] += [day]
                dat[key]['hms']+= [hm]
                dat[key]['lats'] += [lat]
                dat[key]['lons'] += [lon]
                dat[key]['pres'] += [pre]
                dat[key]['speed'] += [spd]
                dat[key]['direction']+= [dr]
                dat[key]['rffs'] += [rff]
                dat[key]['qis']+= [qi]
                dat[key]['intervs'] += [interv]
                 

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
                if key == 'lons':
                    datavars[typ][key] = -1.0 * np.array(map(float, arr))

                    # Crosses dateline
                    if abs(datavars[typ][key].min()) > 179 and abs(datavars[typ][key].max()) > 179:
                        currminlon = np.extract(datavars[typ][key]>0,datavars[typ][key]).min()
                    else:
                        currminlon = datavars[typ][key].min()

                    if currminlon < minlon:
                        minlon = datavars[typ][key].min()
                    if datavars[typ][key].max() > maxlon:
                        maxlon = datavars[typ][key].max()

                elif key in ['pres','speed','direction','rffs','qis','intervs']:
                    datavars[typ][key] = np.array(map(float, arr))
                elif key in ['days','hms']:
                    datavars[typ][key] = np.array(map(int, arr)) 

        nx,ny = (500,500)
        x = np.linspace(minlon, maxlon, nx)
        y = np.linspace(maxlat, minlat, ny)
        gridlons,gridlats = np.meshgrid(x,y)

        for typ in datavars.keys():
            dsname = typ.replace('1d','grid')
            log.info('Interpolating data to grid for %s'%(dsname))
            speed = datavars[typ]['speed']
            direction = datavars[typ]['direction']
            lats = datavars[typ]['lats']
            lons = datavars[typ]['lons']
            pres = datavars[typ]['pres']
            u = (speed * np.cos(np.radians(direction)))#*1.94384
            v = (speed * np.sin(np.radians(direction)))#*1.94384

            # interpolate
            gvars[dsname] = {}
            datavars[dsname] = {}
            gridpres = np.ma.masked_invalid(griddata((lats,lons),pres,(gridlats,gridlons),method='linear'))
            gridu = np.ma.masked_invalid(griddata((lats,lons),u,(gridlats,gridlons),method='linear'))
            gridv = np.ma.masked_invalid(griddata((lats,lons),v,(gridlats,gridlons),method='linear'))
            gridspeed = np.ma.masked_invalid(griddata((lats,lons),speed,(gridlats,gridlons),method='linear'))
            datavars[dsname]['gridpres'] = np.ma.masked_invalid(gridpres)
            datavars[dsname]['gridu'] = np.ma.masked_invalid(gridu)
            datavars[dsname]['gridv'] = np.ma.masked_invalid(gridv)
            datavars[dsname]['gridspeed'] = np.ma.masked_invalid(gridspeed)

            gvars[dsname]['Latitude'] = gridlats
            gvars[dsname]['Longitude'] = gridlons
            clat= 30
            clon = 10
            gridinds = np.where((gridlons>clon) & (gridlons<clon+1) & (gridlats>clat) & (gridlats<clat+1))
            inds = np.where((lons>clon) & (lons<clon+1) & (lats>clat) & (lats<clat+1))

                
        # datavars, gvars, and metadata are passed by reference, so we do not have to return anything.
