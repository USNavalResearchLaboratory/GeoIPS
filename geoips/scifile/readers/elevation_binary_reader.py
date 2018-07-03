# Python Standard Libraries
import logging
from subprocess import Popen, PIPE
import os
from datetime import datetime
from operator import mul
from math import floor, ceil

# Installed Libraries
from IPython import embed as shell
try: from pyhdf.SD import SD,SDC
except: print 'Failed importing pyhdf in scifile/readers/elevation_binary_reader.py. If you need it, install it.'
import numpy as np

# GeoIPS Libraries
from .reader import Reader
from ..containers import DataSet,Variable,_empty_varinfo
from geoips.utils.path.datafilename import DataFileName
from geoips.utils.path.datafilename import StandardAuxDataFileName
from geoips.utils.log_setup import interactive_log_setup

log = interactive_log_setup(logging.getLogger(__name__))

def get_elevation(sector_definition):
    ad = sector_definition.area_definition
    USETOPOFILE = StandardAuxDataFileName.find_existing_file(sectorname=ad.name,
            extdatatype = 'elevation',
            dataprovider = '*',
            extra='*',
            ext='*')
    UNSECTOREDTOPOFILE = StandardAuxDataFileName.find_existing_file(isunsectored=True,
            sectorname=ad.name,
            extdatatype = 'elevation',
            dataprovider = '*',
            extra='*',
            ext='*')
    # Write it out here if needed. Need new timestamp name
    SECTOREDTOPOFILE = StandardAuxDataFileName.frominfo(sectorname=ad.name,
            extdatatype = 'elevation',
            ext='h5' )
    # If the sectorfile needs updated, that means we have to read the UNSECTORED bin file
    # first, and then sector.
    if SECTOREDTOPOFILE.needs_updated():
        # ElevationFile subclass of SciFile has it's own readall, that just pulls out what 
        # it needs from the bin file, much faster than truly reading all the data...
        log.info('USETOPOFILE '+USETOPOFILE)
        log.info('UNSECTOREDTOPOFILE '+UNSECTOREDTOPOFILE)
        log.info('SECTOREDTOPOFILE '+SECTOREDTOPOFILE.name)
        from ..scifile import SciFile
        elev = SciFile() 
        elev.import_data([UNSECTOREDTOPOFILE],sector_definition=sector_definition)
        sectored_elev = elev.sector(ad)
        log.info('    Sectored topo file needs updated: '+SECTOREDTOPOFILE.name)
        sectored_elev.write(SECTOREDTOPOFILE.name)
    # MLS 20150407 If it does not need updated, we can just read the already sectored h5 SciFile
    else:
        # This is no longer an ElevationFile BinFile, it is a SciFile H5File once we've written it out
        from ..scifile import SciFile
        elev = SciFile()
        elev.import_data([USETOPOFILE],sector_definition=sector_definition)
    return elev

# For now must include this string for automated importing of classes.
reader_class_name = 'Elevation_Binary_Reader'
class Elevation_Binary_Reader(Reader):

    dataset_info = { 'TOPO': { 'topo': None } }

    @staticmethod
    def format_test(fname):
        # This reader only handles individual files, not multiple files or directories.
        # Change def read and def format_test if you want to handle directories directly.
        if os.path.isdir(fname):
            return False

        # Check that this file is bin first
        from ..file_format_tests import bin_format_test
        if not bin_format_test(fname):
            return False

        out, err = Popen(['file', '--mime', str(fname)], stdout=PIPE, stderr=PIPE).communicate()
        if ('charset=ebcdic' in out) and ('elevation' in out):
            return True
        # Allow for a link to the actual binary file.
        elif ('application/x-symlink; charset=binary' in out) and ('elevation' in out):
            return True
        else:
            return False

#        df = ncdf.Dataset(str(fname), 'r')
#        if hasattr(df,'source') and df.source == 'ISS RapidScat' and hasattr(df,'institution') and df.institution =='EUMETSAT/OSI SAF/KNMI':
#            return True
#        return False

    def read(self,fname,datavars,gvars,metadata,chans=None,sector_definition=None):
        '''
        Reads all topo data in the region defined by the area definition.
        '''
        self.area_definition=sector_definition.area_definition
        self.shape=(43200,21600)
        crnr_1, crnr_2 = self.corner_coords
        inds = ((crnr_1[0], crnr_2[0], 1), (crnr_1[1], crnr_2[1], 1))
        try:
            xstart, xend, xstep = inds[0]
            ystart, yend, ystep = inds[1]
            shape = (yend-ystart, xend-xstart)
            dims = 2
        #If that fails, try for one dimension
        except TypeError:
            start, end, step = inds
            shape = (end-start,)
            dims = 1

        storage_dtype = np.dtype('>i2')
        fileobj = open(fname, mode='r')

        #If we are only slicing in one dimension
        if dims == 1:
            data_array = self.read_slice(fileobj, start, shape, storage_dtype)
        elif dims == 2:
            lineshape = (xend-xstart,)
            data_array = np.ma.empty(shape, dtype=np.dtype(storage_dtype))
            newline = 0
            for line in range(ystart, yend, ystep):
                start = xstart+line*self.shape[0]
                linedata = self.read_slice(fileobj,start, lineshape, storage_dtype)
                data_array[newline, :] = linedata
                newline += 1

        fileobj.close()

        datavars['TOPO']['topo'] = data_array

        #Create lons and lats
        pixel_size = 30/3600.0 #30 arc seconds
        lonline = np.ma.arange(*inds[0])*pixel_size
        gvars['TOPO']['Longitude'] = np.ma.vstack([lonline for num in range(*inds[1])])
        latsamp = np.ma.arange(*inds[1])*pixel_size
        gvars['TOPO']['Latitude'] = np.ma.hstack([latsamp[np.newaxis].T for num in range(*inds[0])])
        #Convert lons to -180 to 180
        western = gvars['TOPO']['Longitude'] > 180
        gvars['TOPO']['Longitude'][western] = gvars['TOPO']['Longitude'][western]-360

        #Convert lats to -90 to 90
        southern = gvars['TOPO']['Latitude'] > 90
        northern = gvars['TOPO']['Latitude'] <= 90
        gvars['TOPO']['Latitude'][southern] = -(gvars['TOPO']['Latitude'][southern]-90)
        gvars['TOPO']['Latitude'][northern] = np.abs(gvars['TOPO']['Latitude'][northern]-90)

        # Grab necessary metadata that will populate the _finfo, 
        # _dsinfo, and _varinfo properties on the SciFile object.
        # These get passed along when initializing the Variable 
        # instance, then get propagated up to the dsinfo and finfo
        # levels.
        # The available fields for varinfo can be found in 
        # scifile/containers.py at the beginning of the file.
        try:
            sdfn = DataFileName(os.path.basename(fname)).create_standard()
            metadata['top']['start_datetime'] = sdfn.datetime
            metadata['top']['dataprovider'] = sdfn.dataprovider
        except:
            # Set an arbitrary time on the data... Not used for anything anyway...
            metadata['top']['start_datetime'] = datetime.strptime('20150410.000000','%Y%m%d.%H%M%S')
            metadata['top']['dataprovider'] = None
        metadata['top']['end_datetime'] = metadata['top']['start_datetime']
        #metadata['TOPO']['platform_name'] = sdfn.satname
        metadata['top']['platform_name'] = None
#        metadata['TOPO']['filename_datetime'] = varinfo['start_datetime']
        metadata['top']['source_name'] = None

        return 

    @property
    def _lonlats(self):
        if not hasattr(self, '__lonlats'):
            self.__lonlats = self.area_definition.get_lonlats()
        return self.__lonlats

    @property
    def corner_lonlats(self):
        if not hasattr(self, '_corner_lonlats'):
            lons, lats = self._lonlats

            #Make lons 0-360 starting at prime meridian as 0
            western = lons < 0
            lons[western] = 360+lons[western]

            #Make lats 0-180 starting a north pole as 0
            southern = lats < 0
            northern = lats >= 0
            lats[southern] = np.abs(lats[southern])+90
            lats[northern] = np.abs(lats[northern]-90)

            ul_crnr = (lons.min(), lats.min())
            lr_crnr = (lons.max(), lats.max())

            self._corner_lonlats = (ul_crnr, lr_crnr)

        return self._corner_lonlats

    @property
    def corner_coords(self):
        xsize,ysize = self.shape
        crnr_1 = (int(floor(self.corner_lonlats[0][0]*xsize/360.0)), int(floor(self.corner_lonlats[0][1]*ysize/180.0)))
        crnr_2 = (int(ceil(self.corner_lonlats[1][0]*xsize/360.0)), int(ceil(self.corner_lonlats[1][1]*ysize/180.0)))
        return (crnr_1, crnr_2)


    def read_slice(self, fileobj, startpos=0, shape=None, dtype=None, **kwargs):
        #Convert everythin to bytes
        dtype = np.dtype(dtype)
        numsize = dtype.itemsize
        if not shape:
            shape = self.shape
        recordsize = reduce(mul, shape, 1)*numsize
        start = startpos*numsize

        #Seek to correct starting location in file
        fileobj.seek(start)
        data = np.fromstring(fileobj.read(recordsize), dtype=dtype)

        return data



