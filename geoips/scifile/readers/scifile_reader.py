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
import os


# Installed Libraries
import numpy as np
import h5py
from IPython import embed as shell


# GeoIPS Libraries
from .reader import Reader
from ..containers import _empty_varinfo, _empty_dsinfo, _empty_finfo, Variable, DataSet
from ..scifileexceptions import SciFileError

# For now must include this string for automated importing of classes.
reader_class_name = 'SciFile_Reader'
class SciFile_Reader(Reader):
    '''
    This class provides the reader for files written by SciFile.
    All files written by the SciFile package are current written in HDF5 and will follow a common format.
    '''
    # The data set names and variables vary with standard scifile format data files.
    # The reader knows how to pull out the appropriate information.
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

        try:
            fileobj = h5py.File(str(fname), mode='r')
        except IOError:
            return False
        header_fileobj = open(fname, 'r')
        header = header_fileobj.readlines(fileobj.userblock_size)
        fileobj.close()
        header_fileobj.close()
        #If the header starts with "SciFile" then this is a SciFile
        if header[0][0:7] == 'SciFile':
            return True
        else:
            return False

    def read(self,fname,datavars,gvars,metadata,chans=None,sector_definition=None):
        fileobj = h5py.File(fname, 'r')
        _finfo = _empty_finfo.copy()

        #Get the file level attributes
        for attr in fileobj.attrs.keys():
            if attr in _finfo:
                if 'datetime' in attr:
                    _finfo[attr] = datetime.strptime(fileobj.attrs[attr], '%Y%m%d%H%M%S.%f')
                else:
                    _finfo[attr] = fileobj.attrs[attr]
            else:
                raise SciFileError('Unexpected file level attribute encountered: %s' % attr)
        #Loop over the datasets
        for dsname in fileobj.keys():
            dsobj = fileobj[dsname]
            #Should be able to avoid the need for this by separating _dsinfo attributes
            #   into the file level.  May also need to add the ability to do this at the variable level.
            _dsinfo = _empty_dsinfo.copy()
            for attr in dsobj.attrs.keys():
                if attr in _dsinfo:
                    if 'datetime' in attr:
                        _dsinfo[attr] = datetime.strptime(dsobj.attrs[attr], '%Y%m%d%H%M%S.%f')
                    else:
                        _dsinfo[attr] = dsobj.attrs[attr]
                else:
                    raise SciFileError('Unexpected dataset level attribute encountered: %s' % attr)

            vargroup = dsobj['variables']
            for varname in vargroup.keys():
                #print varname
                #Get the variable level attributes
                _varinfo = _empty_varinfo.copy()
                for attr in vargroup[varname].attrs:
                    if attr in _varinfo:
                        if 'datetime' in attr:
                            _varinfo[attr] = datetime.strptime(vargroup[varname].attrs[attr], '%Y%m%d%H%M%S.%f')
                        else:
                            _varinfo[attr] = vargroup[varname].attrs[attr]
                    else:
                        raise SciFileError('Unexpected variable level attribute encountered: %s' % attr)
                if dsname not in datavars.keys():
                    datavars[dsname] = {}
                if _varinfo['badval'] is not None:
                    datavars[dsname][varname] = np.ma.masked_equal(vargroup[varname].value, _varinfo['badval'])
                else:
                    datavars[dsname][varname] = np.ma.array(vargroup[varname].value)
                _varinfo.update(_dsinfo)
                _varinfo.update(_finfo)

            vargroup = dsobj['geolocation']
            for varname in vargroup.keys():
                #print varname
                #Get the variable level attributes
                _varinfo = _empty_varinfo.copy()
                for attr in vargroup[varname].attrs:
                    if attr in _varinfo:
                        if 'datetime' in attr:
                            _varinfo[attr] = datetime.strptime(vargroup[varname].attrs[attr], '%Y%m%d%H%M%S.%f')
                        else:
                            _varinfo[attr] = vargroup[varname].attrs[attr]
                    else:
                        raise SciFileError('Unexpected variable level attribute encountered: %s' % attr)
                if dsname not in gvars.keys():
                    gvars[dsname] = {}
                if _varinfo['badval'] is not None:
                    gvars[dsname][varname] = np.ma.masked_equal(vargroup[varname].value, _varinfo['badval'])
                else:
                    gvars[dsname][varname] = np.ma.array(vargroup[varname].value)
                _varinfo.update(_dsinfo)
                _varinfo.update(_finfo)
                metadata['top'] = _varinfo

        # MLS 20170105
        # I have no idea what is going on here - shape is getting set to [width,height] 
        # and everyhting else is (width,height).  Brute force it into shape for now.
        # At some point we're going to have to do some major reworking of this, but 
        # for now I'm just making it work...
        metadata['top']['shape'] = (metadata['top']['shape'][0],metadata['top']['shape'][1])
    
        return 
