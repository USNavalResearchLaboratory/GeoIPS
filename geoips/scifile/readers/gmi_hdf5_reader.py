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


# Installed Libraries
import h5py
import numpy as np
from numpy import asscalar as assc
from IPython import embed as shell


# GeoIPS Libraries
from ..scifileexceptions import SciFileError
from ..containers import DataSet, Variable, _empty_varinfo
from .reader import Reader
from geoips.utils.path.datafilename import DataFileName

log = logging.getLogger(__name__)

def get_header_info(header,field):
    head = header.split(';\n')
    for ii in head:
        if field in ii:
            fld,val = ii.split('=')
            return val
    return None

# For now must include this string for automated importing of classes.
reader_class_name = 'GMI_HDF5_Reader'
class GMI_HDF5_Reader(Reader):
    # dataset_info[dsname][geoipsvarname] = origdatavarname
    dataset_info = { 'S1': { 'tb10v': 0,
                         'tb10h': 1,
                         'tb19v': 2,
                         'tb19h': 3,
                         'tb23v': 4,
                         'tb37v': 5,
                         'tb37h': 6,
                         'tb89v': 7,
                         'tb89h': 8,},
                 'S2': { 'tb166v': 0,
                         'tb166h': 1,
                         'tb183_3v': 2,
                         'tb183_7v': 3}
             }
        
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

        try:
            fileobj = h5py.File(str(fname), mode='r')
        except IOError:
            return False
        if not hasattr(fileobj,'attrs') or 'FileHeader' not in fileobj.attrs.keys():
            return False
        if 'SatelliteName=GPM' not in fileobj.attrs['FileHeader'] and 'InstrumentName=GMI' not in fileobj.attrs['FileHeader']:
            return False
        fileobj.close()
        return True

    def read(self,fname,datavars,gvars,metadata,chans=None,sector_definition=None):
        fileobj = h5py.File(str(fname), mode='r')

        header = fileobj.attrs['FileHeader']
        metadata['top']['platform_name'] = get_header_info(header,'SatelliteName').lower()
        metadata['top']['source_name'] = get_header_info(header,'InstrumentName').lower()
        dfn = DataFileName(os.path.basename(fname))
        if dfn:
            sdfn = dfn.create_standard()
            metadata['top']['dataprovider'] = sdfn.dataprovider 
        else:
            metadata['top']['dataprovider'] = 'Unknown'


        for dsname in self.dataset_info.keys():

            londata = fileobj[dsname]['Longitude'].value
            latdata = fileobj[dsname]['Latitude'].value

            yyyy = fileobj[dsname]['ScanTime']['Year'].value
            mm = fileobj[dsname]['ScanTime']['Month'].value
            dd = fileobj[dsname]['ScanTime']['DayOfMonth'].value
            hh = fileobj[dsname]['ScanTime']['Hour'].value
            mn = fileobj[dsname]['ScanTime']['Minute'].value
            ss = fileobj[dsname]['ScanTime']['Second'].value

            metadata['top']['start_datetime'] = datetime.strptime("%04d%02d%02d%02d%02d%02d"%(yyyy[0],mm[0],dd[0],hh[0],mn[0],ss[0]),'%Y%m%d%H%M%S')
            # Note an apparent bug in productfilename uses end_datetime as filename. 
            # For now just leave out end_datetime (it automatically gets set to start_datetime
            # in scifile if undefined)
            # Ooops, this might have messed up pass predictor
            metadata['top']['end_datetime'] = datetime.strptime("%04d%02d%02d%02d%02d%02d"%(yyyy[-1],mm[-1],dd[-1],hh[-1],mn[-1],ss[-1]),'%Y%m%d%H%M%S')
            metadata['top']['filename_datetime'] = metadata['top']['start_datetime']

            # Tells driver to NOT try to sector this data.
            metadata['top']['NON_SECTORABLE'] = True

            if chans == []:
                return

            numchans = fileobj[dsname]['Tb'].value.shape[2]
            tbdatalist = np.dsplit(fileobj[dsname]['Tb'].value,numchans)
            tbdata = []

            ii= 0
            for data in tbdatalist:
                for currgeoipsvarname,ncbandnum in self.dataset_info[dsname].items():
                    if ii == ncbandnum:
                        geoipsvarname = currgeoipsvarname
                if not chans or geoipsvarname in chans:
                    datavars[dsname][geoipsvarname] = np.ma.masked_equal(np.squeeze(data),-999)
                ii += 1
            gvars[dsname]['Latitude'] = latdata
            gvars[dsname]['Longitude'] = londata
            metadata['gvars'][dsname]['Longitude'] = _empty_varinfo.copy()
            metadata['gvars'][dsname]['Latitude'] = _empty_varinfo.copy()
            metadata['gvars'][dsname]['Longitude']['nomask'] = True
            metadata['gvars'][dsname]['Latitude']['nomask'] = True

        return 
