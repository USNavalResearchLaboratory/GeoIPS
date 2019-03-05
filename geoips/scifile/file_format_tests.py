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
import os
import bz2
from subprocess import Popen, PIPE, call
# Installed Libraries
# Don't fail if these don't exist, only needed for certain readers.
try:
    from pyhdf.HDF import ishdf
except:
    print 'Failed importing pyhdf in scifile/readers/format_tests.py. If you need it, install it.'

try: 
    import pygrib as pg
except: 
    print 'Failed importing pygrib in scifile/file_format_tests.py. If you need it, install it.'

try:
    from h5py import is_hdf5
except:
    print 'Failed importing h5py in scifile/readers/format_tests.py. If you need it, install it.'

try:
    import netCDF4 as ncdf
except:
    print 'Failed importing netCDF4 in scifile/readers/format_tests.py. If you need it, install it.'

# from IPython import embed as shell

# GeoIPS Libraries
from .scifileexceptions import MultiMatchingReadersError,NoMatchingReadersError
from . import readers


def grib_format_test(fname):
    try:
        #print 'Entering debug shell in scifile/readers/format_tests.py/grib_format_test'
        #shell()
        # I think we're going to have to rely on filenames here...
        if 'US058GMET' not in fname and 'US058GOCN' not in fname \
                and 'US058GLND' not in fname and 'US058GCOM' not in fname :
            return False
        df = pg.open(fname)
        if df.messages:
            df.close()
            return True
        df.close()
        return False
    except:
        return False


def hdf4_format_test(fname):
    # print 'Entering debug shell in scifile/readers/format_tests.py/hdf4_format_test'
    try:
        parts = fname.split('.')
        if parts[-1] not in ['hdf', 'hdf4', 'he4']:
            return False
        return ishdf(str(fname))
    except:
        return False


def hdf5_format_test(fname):
    # print 'Entering debug shell in scifile/readers/format_tests.py/hdf5_format_test'
    # shell()
    # PROBABLY NEED TO FIGURE OUT WHAT EXCEPTION TO ACTUALLY CATCH FOR ALL OF THESE...
    # Don't just do blanket try/except.
    parts = fname.split('.')
    if parts[-1] not in ['h5', 'hdf5']:
        return False
    try:
        return is_hdf5(str(fname))
    except:
        return False


def ncdf3_format_test(fname):
    try:
        # print 'Entering debug shell in scifile/readers/format_tests.py/ncdf3_format_test'
        # shell()
        parts = fname.split('.')
        if parts[-1] not in ['nc', 'nc3']:
            return False
        df = ncdf.Dataset(str(fname), 'r')
        data_model = df.data_model
        df.close()
        if data_model in ['NETCDF3_CLASSIC', 'NETCDF3_64BIT']:
            return True
        else:
            return False
    except:
        return False


def ncdf4_format_test(fname):
    try:
        # print 'Entering debug shell in scifile/readers/format_tests.py/ncdf4_format_test'
        # shell()
        parts = fname.split('.')
        if parts[-1] not in ['nc', 'nc4','h5']:
            return False
        df = ncdf.Dataset(str(fname), 'r')
        data_model = df.data_model
        df.close()
        if data_model in ['NETCDF4', 'NETCDF4_CLASSIC']:
            return True
        else:
            return False
    except:
        return False

def ascii_format_test(fname):
    try:
        with open(fname) as f:
            line = f.readline()
        try:
            line.decode('ascii')
        except UnicodeDecodeError:
            return False
        else:
            return True 
    except:
        return False


def bz2_format_test(fname):
    try:
        parts = fname.split('.')
        # Force bz2 extension for now
        if parts[-1] not in ['bz2']:
            return False
        df = bz2.BZ2File(str(fname), 'r')
        df.readline()
    except:
        return False
    return True


def hsd_format_test(fname):
    try:
        parts = fname.split('.')
        if parts[-1] not in ['DAT']:
            return False
        df = open(str(fname), 'r')
        line = df.readline()
        if 'Himawari-8' in line:
            return True
        else:
            return False
    except:
        return False

    return False


def bin_format_test(fname):
    # print 'Entering debug shell in scifile/readers/format_tests.py/bin_format_test'
    # shell()
    if '.bin' not in fname and '.raw' not in fname and 'fcstfld' not in fname:
        return False
    out, err = Popen(['file', '--mime', str(fname)], stdout=PIPE, stderr=PIPE).communicate()
    if ('charset=ebdic' in out) or ('charset=binary' in out) or ('charset=ebcdic' in out):
        return True
    else:
        return False


def xpif_format_test(fname):
    if not bin_format_test(fname):
        return False
    if os.path.splitext(fname)[1].lower() == '.xpif':
        return True
    else:
        return False


def get_reader(fname):
    '''
    Find the data reader that matches the input data file.
    Will raise a SciFile Error if no matching reader is found,
    or multiple matching readers are found.
    '''

    reader_list = []
    # list all readers, dynamically set in __init__.py to every module in scifile/readers/*.py:
    #print readers.__all__
    for modulename in readers.__all__:
        module = getattr(readers, modulename)
        #print module
        if not hasattr(module, 'reader_class_name'):
            continue
        reader = getattr(module, module.reader_class_name)()
        #print reader
        if reader.format_test(fname):
            reader_list += [reader]

    if len(reader_list) > 1:
        call(['ls','--full-time',fname])
        raise MultiMatchingReadersError('More than one reader matched format - FIX! ' + str(reader_list))
    elif not reader_list:
        call(['ls','--full-time',fname])
        raise NoMatchingReadersError('No matching reader found')
    else:
        return reader_list[0]
