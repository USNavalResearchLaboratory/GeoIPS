#!/bin/env python

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
import pdb
import shutil
import os
import logging
from datetime import datetime,timedelta
from glob import glob

# Installed Libraries
# Don't fail if this doesn't import, not even used at the moment.
try: from memory_profiler import profile
except: print 'Failed importing memory_profiler in scifile/scifile.py. If you need it, install it.'
import numpy
from lxml import objectify
#h5py is imported late to avoid a conflict between lxml and h5py
#Importing in the other order segfaults
#Probably because h5py has an in-built version of lxml that is not supported by
#   the system libraries, but I'm not entirely sure.
import h5py
from IPython import embed as shell

# GeoIPS Libraries
#from geoips.utils.decorators import deprecated
from geoips.utils.path.datafilename import DataFileName
#from geoips.utils.memusg import print_mem_usage
from . import file_format_tests
from .containers import *
from .scifileexceptions import SciFileError,NoMatchingReadersError,MultiMatchingReadersError


log = logging.getLogger(__name__)

class SciFile(object):
    def __new__(cls):
        obj = object.__new__(cls)
        obj.datafiles = {}
        obj.datasets = DataSetContainer(obj)
        obj._finfo = _empty_finfo.copy()
        return obj

    def __getitem__(self, index):
        #Can only do this if we only have one dataset in the SciFile instance
        if len(self.datasets) == 0:
            raise IndexError('Cannot index empty %s' % self.__class__)
        elif len(self.datasets) > 1:
            raise IndexError('Cannot index when more than one DataSet exists.  Register first.')

        #Create a new SciFile object
        new = self.__class__()

        #Index the DataSet object
        ds = self.datasets.values()[0]
        new._add_dataset(ds[index])
        return new

    # MLS 20160203 in an effort to save memory and stop 
    #   storing subset of data separately from full datafile,
    #   begin testing full datafile on existence of variables
    #   as a first test of whether we should run.
    def has_any_vars(self,required_vars):
        # def variables goes through all datasets and 
        # adds the individual variables to self.variables - 
        # so this has everything.
        scifile_vars = set(self.variables.keys())
        required_vars = set(required_vars)
        # If there are any vars in common between the two,
        # return True
        if required_vars.intersection(scifile_vars):
            return True
        return False

    # MLS 20160203 in an effort to save memory and stop 
    #   storing subset of data separately from full datafile,
    #   begin testing full datafile on existence of variables
    #   as a first test of whether we should run.
    def has_all_vars(self,required_vars):
        # def variables goes through all datasets and 
        # adds the individual variables to self.variables - 
        # so this has everything.
        scifile_vars = set(self.variables.keys())
        required_vars = set(required_vars)
        # If all vars in required_vars are in  
        # dataset vars, return True.
        # return True
        if required_vars.issubset(scifile_vars):
            return True
        return False

    def similar(self, other):
        '''
        Compare the SciFile instance with another SciFile, a DataSet, or a Variable to determine similarity.
        Similarity is determined by whether specific properties of the SciFile instance are equal to
        the same properties in the input object.  These properties are defined by the contents of
        `self._finfo`.  The specific properties can be determined by examining scifile.containers._empty_finfo.

        Returns True if similar and False if not similar.
        '''
        #  May want to not always adjust datetimes... But for now, we don't 
        # really care, as long as they match throughout
        self.adjust_datetimes(other)

        for attr in self._finfo.keys():
            selfattr = getattr(self, attr)
            otherattr = getattr(other, attr)
            #print 'selfattr: '+str(attr)+' '+str(selfattr)
            #print 'otherattr: '+str(attr)+' '+str(otherattr)
            if selfattr is not None and otherattr is not None and selfattr != otherattr:
                #print 'selfattr: '+str(attr)+' '+str(selfattr)
                #print 'otherattr: '+str(attr)+' '+str(otherattr)
                return False
        return True

    #def _create_similar(self, datasets=None, variables=None):
    #    '''
    #    Create a new SciFile instance where all initial values are the same as the current instance,
    #    but the DataSets and/or Variables have been replaced with the input Variable list.
    #    '''
    #    newobj = self.__class__()
    #    if datasets is not None:

    #@property
    #def geolocation_variables(self):
    #    if len(self.datasets) == 1:
    #        key = self.datasets.keys()[0]
    #        return self.datasets[key].geolocation_variables
    #    else:
    #        return None

    @property
    def userblock(self):
        '''Returns the userblock for a SciFile instance as an lxml.objectify._ElementTree instance.'''
        root = objectify.Element('datamap')
        for ds in self.datasets.values():
            root.append(ds._userblock)
        return root.getroottree()

    def create_subset(self, variables=[], geolocation_variables=[]):
        '''
        Returns a new instance of SciFile containing copies of the specified datasets and variables.
        The resulting instance will contain only those variables, geolocation variables, and datasets
        that are requested.

        Required variables should be specified as a list of strings.  Each string should be of the form:
            dataset_name/variable_name
        If a variable or an entire dataset is missing, a KeyError will be raised.

        If no variables are requested, an empty SciFile instance will be returned.
        If variables are requested, the resulting SciFile instance will contain only those DataSets
            required to contain the requested variables.

        By default, the DataSets in the new instance will contain all available geolocation variables.
        If geolocation variables are specifically requested, all other geolocation variables will be
            dropped.
        Geolocation variables are specified as a list of strings, but unlike variables, the dataset name
            should be left off.  All datasets will carry the same geolocation variables as available.
        No error will be raised for missing geolocation variables.
        '''
        cls = self.__class__
        new = cls.__new__(cls)
        new.metadata = self.metadata.copy()

        #Split out the dataset and viarable for each requested variable
        vars_to_gather = {}
        for varname in variables:
            try:
                dsname = self.variables[varname].dataset.name
                if not vars_to_gather.has_key(dsname):
                    vars_to_gather[dsname] = [varname]
                else:
                    vars_to_gather[dsname].append(varname)
            except KeyError:
                log.warning('No such variable %s.  Will not be included in subset.' % varname)
                continue

        #Loop over required datasets
        for dsname in vars_to_gather.keys():
            try:
                curr_ds = self.datasets[dsname]
            except KeyError:
                raise KeyError('No such dataset %s' % dsname)
            new_ds = curr_ds.create_subset(variables=vars_to_gather[dsname],
                                           geolocation_variables=geolocation_variables
                                          )
            new.add_dataset(new_ds)
            #if new_ds:
            #    # MLS 20150107 ?????????
            #    new_ds._sensor_name = self.sensor_name
            #    new_ds._dataprovider = self.dataprovider
            #    new_ds._platform_name = self.platform_name
            #    new.datasets.append(new_ds)

            #if new.variables:
            #    new._sensor_name = self.sensor_name
            #    new._dataprovider = self.dataprovider
            #    new._platform_name = self.platform_name
            #    new.geostationary = self.geostationary

        if len(new.variables) > 0:
            return new
        else:
            return None

    def readall(self):
        '''Forces all data referecenced byt his object to be read into memory.'''
        for ds in self.datasets.values():
            ds.readall()

    def write_txtfiles(self):
        ''' Currently this is exclusively for RSCAT data. We need to look into standardizing
        variable names, flag values, etc if this is going to be used for additional Data 
        types.  This writes out txt files formatted for ATCF ingest, and copies 
        them into ftp directory'''

        log.info('In write_txtfile')
        dfn = DataFileName(os.path.basename(self.datafiles.keys()[0]))
        sdfn = dfn.create_standard()
        sdfn.ext = 'atcftxt'
        header_written = False
        for chan in self.datasets.keys():
            if chan == 'PRIMARY':
                sdfn.channel = 'primary' 
            elif chan == 'AMB':
                sdfn.channel = 'ambiguities'
                log.info('Skipping ambiguities for now')
                continue
            elif chan == 'TIME':
                log.info('dont go through TIME!')
                continue
            log.info('Channel: '+str(chan))
            winddirs = self.datasets[chan].variables['retrieved_wind_direction']
            windspds = self.datasets[chan].variables['retrieved_wind_speed']
            lats = self.datasets[chan].geolocation_variables['Latitude']
            lons = self.datasets[chan].geolocation_variables['Longitude']
            flags = self.datasets[chan].variables['flags']
            sdfn.makedirs()
            log.info('Writing wind vectors to '+sdfn.name)
            if os.path.exists(sdfn.name):
                log.info('Not overwriting file, quitting')
                continue
            txtfile = open(sdfn.name,'w')
            num = 0
            actually_written = 0
            skipped_flags = 0
            basedt = datetime.strptime('1999.01.01 00:00:00','%Y.%m.%d %H:%M:%S')
            for ii in range(winddirs.shape[0]):
                currtime = self.datasets['TIME'].variables['time'].data[ii]
                currdt = basedt + timedelta(seconds=currtime)
                for jj in range(winddirs.shape[1]):
                    if winddirs.data[ii][jj] is not numpy.ma.masked:
                        if not header_written:
                            txtfile.write('METXSCT '+currdt.strftime('%Y%m%d%H%M')+' ASC (12 HOURS WORTH)\n')
                            header_written = True
                        currlon = lons.data[ii][jj]
                        if lons.data[ii][jj] > 180:
                            currlon = lons.data[ii][jj] - 360
                        currdir = winddirs.data[ii][jj]
                        if winddirs.data[ii][jj] >= 180:
                            currdir = winddirs.data[ii][jj] - 180
                        else:
                            currdir = winddirs.data[ii][jj] + 180
                        #currflag = ''.join([str(int(flags[ii][jj])>>i&1) for i in range(14,-1,-1)])
                        ## bit 14, 16384
                        #available_data_flag = currflag[0]
                        ## bit 13, 8192
                        #rain_impact_flag = currflag[1]
                        ## bit 12, 4096
                        #rain_impact_flag_usable = currflag[2]
                        ## bit 11, 2048
                        #low_wind_speed_flag = currflag[3]
                        ## bit 10, 1024
                        #high_wind_speed_flag = currflag[4]
                        ## bit 9, 512
                        #wind_retrieval_flag = currflag[5]
                        ## bit 8, 256
                        #ice_edge_flag = currflag[6]
                        ## bit 7, 128
                        #coastal_flag = currflag[7]
                        ## bit 1, 2
                        #adequate_azimuth_diversity_flag = currflag[-2]
                        ## bit 0, 1
                        #adequate_sigma0_flag = currflag[-1]
                        if int(flags.data[ii][jj]) == 20480:
                            txtfile.write(' SCT %8.1f %6.1f %03d %3d %s\n'%(lats.data[ii][jj],
                                currlon,
                                currdir,
                                windspds.data[ii][jj]*1.94384,
                                str(currdt.strftime('%Y%m%d%H%M')),
                                ))
                            #txtfile.write(' SCT %8.1f %6.1f %03d %3d %s %6d %s availdata: %s rain: %s rainuse: %s lowwind: %s\n'%(lats[ii][jj],
                            #        currlon,
                            #        currdir,
                            #        windspds[ii][jj]*1.94384,
                            #        str(currdt.strftime('%Y%m%d%H%M')),
                            #        flags[ii][jj],
                            #        currflag,
                            #        available_data_flag,
                            #        rain_impact_flag,
                            #        rain_impact_flag_usable,
                            #        low_wind_speed_flag,
                            #        ))
                            actually_written += 1
                        else:
                            skipped_flags += 1
                    num += 1
                    if num % 10000 == 0:
                        log.info('Checking number '+str(num)+' of '+\
                            str(winddirs.size)+' Actually written: '+\
                            str(actually_written)+' Skipped: '+str(skipped_flags))
            txtfile.close()
            log.info('Copying: '+sdfn.name+' to '+os.getenv('FTPROOT')+'/satdata/for_atcf/'+os.path.basename(sdfn.name))
            shutil.copyfile(sdfn.name,os.getenv('FTPROOT')+'/satdata/for_atcf/'+os.path.basename(sdfn.name))
    

    def write(self, fname=None, variables=None, geolocation_variables=None, mode='w-'):
        '''Write the contained data out to a standard SciFile hdf5 file.
        Need to describe this data format in detail...
        If variables or geolocation_variables are None, then include ALL variables of that type.
        If variables or geolocation_variables are [], explicitly stating we want NO variables included
            of that type.
        If you want to specify a list of variables, must include geolocation_variables and variables 
            (otherwise, the one that is not included will include all variables of that type, in addition
            to the ones you specified)
        '''
        #Using StringIO to obtain an in-memory file-like object
        if not fname:
            sdfn = DataFileName().create_standard(scifile_obj=self)
            if variables == None and geolocation_variables == None:
                sdfn.channel = 'all'
            elif variables and geolocation_variables:
                sdfn.channel = '-'.join(['-'.join(variables), '-'.join(geolocation_variables)])
            elif variables:
                sdfn.channel = '-'.join(variables)
            elif geolocation_variables:
                sdfn.channel = '-'.join(geolocation_variables)
            sdfn.makedirs()
            fname = sdfn.name

        #Open the file for writing
        df = h5py.File(fname, mode, userblock_size=512)

        #Open the userblock for writing (open file as a normal file)
        df_userblock = open(fname, 'w')
        df_userblock.write('SciFile')

        #Write file level attributes
        for attr in self._finfo.keys():
            val = getattr(self, attr)
            if val is not None:
                #datetime objects must be handled specifically on write and read
                if isinstance(val, datetime):
                    df.attrs[attr] = val.strftime('%Y%m%d%H%M%S.%f')
                else:
                    df.attrs[attr] = val

        log.info('Writing metadata dictionary out to hdf5 file')
        # Save the full metadata dictionary into the METADATA dataset in h5 file
        from .utils import save_dict_to_hdf5
        save_dict_to_hdf5(self.metadata, df, 'METADATA')
        log.info('Done writing metadata dictionary out to hdf5 file')

        #Loop over datasets and call their write method
        for ds in self.datasets.values():
            ds.write(df, variables, geolocation_variables)

        #Close the userblock
        df_userblock.close()

        #Close the file
        df.close()

    def import_metadata(self, paths):
        ''' INPUTS: list of paths
            OUTPUTS: None (just populates SciFile Object with metadata.
        import_metadata reads in the minimal amount of 
            information from the data file to populate the 
            varinfo fields. Useful for figuring out the 
            platform_name, source_name, start_datetime, etc
            without having to read in all of the data.'''
        ignore = ['.meta', '.processing']

        fnames = self.expand_filename_list(paths)

        # Initialize the Data Dictionaries
        gvars = {}
        datavars = {}
        metadata = {} 
        datasets = []

        # Explicitly request NO channels, different from None (meaning you want all channels)
        # This will just set up all the necessary metadata.
        # Keep trying files in the directory until one sets start_datetime (that is required
        #   metadata. With everything so far, that works on the first file)
        for fname in fnames:
            self.__import_datafile(fname,datavars,gvars,metadata,chans=[])
            for readername in metadata.keys():
                if metadata[readername]['top']['start_datetime']:
                    break
        # Create dummy dataset with metadata if we didn't read anything yet.
        for readername in metadata.keys():
            # Find the one that actually populated...
            if metadata[readername]['top']['start_datetime']:
                metadata_variables = [Variable('metadata',data=numpy.ma.array([]),_varinfo=metadata[readername]['top'])]
                datasets = [DataSet('METADATA',variables=metadata_variables,geolocation_variables=[],copy=False)]

            metadata[readername]['top']['readername'] = readername

        self.metadata = metadata[readername]
        self.add_datasets(datasets)

    def expand_filename_list(self,paths):
        #Raise an error if the path doesn't exist
        # Compile a list of individual files
        fnames = []
        for path in paths:
            if not os.path.exists(path):
                raise IOError('No such file or directory: %s' % path)
            if os.path.isdir(path):
                # First try reading the entire directory at once - format_tests should 
                # take this into account, if the format expressly requires a directory of 
                # files at once, or a single file at a time.
                try:
                    reader = file_format_tests.get_reader(path)
                    fnames += [path]
                # If no readers matched, try individual files instead of complete directory
                except NoMatchingReadersError:
                    fnames += glob(os.path.join(path,'*'))
                # If multiple readers matched, that is a problem. Raise.
                except MultiMatchingReadersError:
                    raise
            else:
                fnames += [path]
        return fnames

    def import_data(self, paths, chans=None, sector_definition=None, self_register=False):

        if chans != []:
            log.info('IMPORTING DATA %s' % str(paths))

        #Extensions to ignore
        ignore = ['.meta', '.processing']

        fnames = self.expand_filename_list(paths)

        # Initialize the Data Dictionaries
        gvars = {}
        datavars = {}
        metadata = {} 
        datasets = []

        for fname in sorted(fnames):
            # Passed by reference, import_datafile modifies gvars, datavars, and metadata
            self.__import_datafile(fname, datavars, gvars, metadata, chans=chans,
                                   sector_definition=sector_definition, self_register=self_register)

        for readername in gvars.keys():
            for dsname in gvars[readername].keys():
                geolocation_variables = []
                for varlabel in gvars[readername][dsname].keys():
                    try:
                        nomaskval = metadata[readername]['gvars'][dsname][varlabel]['nomask']
                    except:
                        nomaskval = False
                    geolocation_variables += [Variable(varlabel,data=gvars[readername][dsname][varlabel],_varinfo=metadata[readername]['top'],_nomask=nomaskval)]
                if geolocation_variables:
                    datasets += [DataSet(dsname,geolocation_variables=geolocation_variables,copy=False)]
            metadata[readername]['top']['readername'] = readername

        for readername in datavars.keys():
            for dsname in datavars[readername].keys():
                variables = []
                for varlabel in datavars[readername][dsname].keys():
                    try:
                        nomaskval = metadata[readername]['datavars'][dsname][varlabel]['nomask']
                    except:
                        nomaskval = False
                    variables += [Variable(varlabel,data=datavars[readername][dsname][varlabel],_varinfo=metadata[readername]['top'],_nomask=nomaskval)]
                if variables:
                    datasets += [DataSet(dsname,variables=variables,copy=False)]
            metadata[readername]['top']['readername'] = readername
        self.metadata = metadata[readername]

        self.add_datasets(datasets)


    def add_datasets(self,datasets):

        #Attach datasets to current instance
        for dataset in datasets:
            try:
                self.add_dataset(dataset, copy=False)
            except ValueError,resp:
                log.warning(str(resp)+' SKIPPING DATASET '+dataset.name+'!!')
                continue
    
        if datasets and self.platform_name and self.source_name and self.runfulldir == None:
            self._finfo['runfulldir'] = DataFileName.from_satsensor(self.platform_name,self.source_name,wildcards=True).sensorinfo.FName['runfulldir']

    def __import_datafile(self, fname, datavars, gvars, metadata, chans=None, sector_definition=None,
                          self_register=False):


        if not os.path.exists(fname):
            raise IOError('Input path does not exist: %s' % fname)

        #Obtain a reader for the input datafile
        try:
            # Use scifile/format_tests.py and scifile/<READERNAME>.py/format_test to determine
            # which reader we need to use.
            reader = file_format_tests.get_reader(fname)

            # Loop through all of the dataset labels found in the reader dataset_info.
            # dataset_info is a list of channels and datasets they belong to. Must exist!
            # If we don't read any data from a particular dataset, it will just be empty.
            # If this is empty, the reader itself will have to initialize the dictionaries.
            # Having the extra "readername" level allows having more than one data type
            # in the same SciFile object, which would allow for true data fusion..
            readername = reader.__class__.__name__
            if readername not in metadata.keys():
                metadata[readername] = {}
            if readername not in datavars.keys():
                datavars[readername] = {}
            if readername not in gvars.keys():
                gvars[readername] = {}

            if 'top' not in metadata[readername].keys():
                metadata[readername]['top'] = _empty_varinfo.copy()
            if 'ds' not in metadata[readername].keys():
                metadata[readername]['ds'] = {}
            if 'datavars' not in metadata[readername].keys():
                metadata[readername]['datavars'] = {}
            if 'gvars' not in metadata[readername].keys():
                metadata[readername]['gvars'] = {}

            alldatasetnames = []
            if hasattr(reader,'dataset_info'):
                alldatasetnames += reader.dataset_info.keys()
            if hasattr(reader,'gvar_info'):
                alldatasetnames += reader.gvar_info.keys()
            for dsname in alldatasetnames:
                if dsname not in datavars[readername].keys():
                    datavars[readername][dsname] = {}
                if dsname not in gvars[readername].keys():
                    gvars[readername][dsname] = {}
                if dsname not in metadata[readername]['ds'].keys():
                    metadata[readername]['ds'][dsname] = _empty_varinfo.copy()
                if dsname not in metadata[readername]['datavars'].keys():
                    metadata[readername]['datavars'][dsname] = {}
                if dsname not in metadata[readername]['gvars'].keys():
                    metadata[readername]['gvars'][dsname] = {}

            #Read datasets from the datafile
            # Dictionaries are passed by reference, so the reader will modify datavars, gvars, and metadata in place.
            if self_register:
                reader(fname, datavars[readername], gvars[readername], metadata[readername], chans=chans,
                   sector_definition=sector_definition, self_register=self_register)
            else:
                # There is probably a better way to handle varying def read call signatures (kwargs ?), but 
                # for now, only try to pass self_register if it is true, since only abi and ahi readers have
                # it defined.
                reader(fname, datavars[readername], gvars[readername], metadata[readername], chans=chans,
                   sector_definition=sector_definition)
    
            #print str(self.datasets.keys())+' '+str(self.geolocation_variables.keys())+' '+str(self.variables.keys())

            self.datafiles[fname] = None

        except SciFileError:
            # Print out exception instead of just warning, so we can see WHY it failed.
            log.exception('Skipping file, reader failed')


    def add_variable(self, data, name=None, copy=True, _geoloc=True, _force=False):
        '''
        Appends a variable to the SciFile.  May add a new DataSet if required.
        '''
        if not self.similar(data):
            raise SciFileError('Cannot add Variable to SciFile.  Not similar.')
        if name is None:
            try:
                name = data.name
            except AttributeError:
                raise ValueError('Input data must either be a Variable instance or name keyword must be provided.')
        if copy:
            data = data._create_similar(data, name=name)

        #Loop over datasets and check for similarity
        added = False
        for dsname, ds in self.datasets.items():
            if ds.similar(data):
                ds.add_variable(data, _force=_force)
                added = True
        if not added:
            dsname = '_%s_%s' % (data.source_name, data.platform_name)
            ds = DataSet(dsname, variables=[data], copy=False, _finfo=self._finfo)
            self.add_dataset(ds, copy=False)


    def adjust_datetimes(self, dataset):

        # scifile does not allow any of the "info" dictionary values
        # to differ between datasets / variables within the object.
        # Sometimes start/end datetimes don't match (like himawari)
        # Was previously in create_subset and _import_datafile
        # try standardizing here and call from add_dataset, 
        # adjust start/end_datetime to match throughout scifile object 
        # (all datasets, variables, and file) This is way overkill

        new_start_datetime = None
        new_end_datetime = None

        #print datetime.utcnow()
        if self.start_datetime:
            #print 'new is self start '+str(self.start_datetime)
            new_start_datetime = self.start_datetime
        elif dataset.start_datetime:
            #print 'new is dataset start '+str(dataset.start_datetime)
            new_start_datetime = dataset.start_datetime
        if self.end_datetime:
            #print 'new is self end '+str(self.end_datetime)
            new_end_datetime = self.end_datetime
        elif dataset.end_datetime:
            #print 'new is dataset end '+str(dataset.end_datetime)
            new_end_datetime = dataset.end_datetime

        if dataset.start_datetime and new_start_datetime:
            #print 'Checking new dataset / self start'
            if dataset.start_datetime < new_start_datetime:
                #print str(dataset.name)+'st dataset < new'
                new_start_datetime = dataset.start_datetime
        if new_end_datetime and dataset.end_datetime:
            #print 'Checking new dataset / self end'
            if dataset.end_datetime > new_end_datetime:
                #print str(dataset.name)+'end dataset > new'
                new_end_datetime = dataset.end_datetime

        for ds in self.datasets.values():
            if ds.start_datetime and new_start_datetime:
                #print 'Checking existing dataset / new start'
                if ds.start_datetime < new_start_datetime:
                    #print str(ds.name)+'st ds < new'
                    new_start_datetime = ds.start_datetime
            if ds.end_datetime and new_end_datetime:
                #print 'Checking existing dataset / new end'
                if ds.end_datetime > new_end_datetime:
                    #print str(ds.name)+'end ds > new'
                    new_end_datetime = ds.end_datetime
            for var in ds.variables.values():
                if var.start_datetime and new_start_datetime:
                    #print 'Checking existing var / new start'
                    if var.start_datetime < new_start_datetime:
                        #print str(var.name)+'st var < new'
                        new_start_datetime = var.start_datetime
            for var in ds.variables.values():
                if var.end_datetime and new_end_datetime:
                    #print 'Checking existing var / new end'
                    if var.end_datetime > new_end_datetime:
                        #print str(var.name)+'end var > new'
                        new_end_datetime = var.end_datetime
                        
        # Set self start/end_datetime
        if new_start_datetime and self.start_datetime != new_start_datetime:
            #print str(self)+' st '+str(self.start_datetime)+' to '+str(new_start_datetime)
            self._finfo['start_datetime'] = new_start_datetime
        if new_end_datetime and self.end_datetime != new_end_datetime:
            #print str(self)+' end '+str(self.end_datetime)+' to '+str(new_end_datetime)
            self._finfo['end_datetime'] = new_end_datetime

        # Set start/end_datetime on new dataset that we are about to add
        if new_start_datetime and dataset.start_datetime != new_start_datetime:
            #print str(dataset.name)+' newds st '+str(dataset.start_datetime)+' to '+str(new_start_datetime)
            dataset.start_datetime = new_start_datetime
        if new_end_datetime and dataset.end_datetime != new_end_datetime:
            #print str(dataset.name)+' newds end '+str(dataset.end_datetime)+' to '+str(new_end_datetime)
            dataset.end_datetime = new_end_datetime

        # set start/end_datetime on all existing datasets
        for ds in self.datasets.values():
            if new_start_datetime and ds.start_datetime != new_start_datetime:
                #print str(ds.name)+' existingds st '+str(ds.start_datetime)+' to '+str(new_start_datetime)
                ds.start_datetime = new_start_datetime
            if new_end_datetime and ds.end_datetime != new_end_datetime:
                #print str(ds.name)+' existingds end '+str(ds.end_datetime)+' to '+str(new_end_datetime)
                ds.end_datetime = new_end_datetime
            # Set start/end_datetime on all existing variables
            for var in ds.variables.values():
                if new_start_datetime and var.start_datetime != new_start_datetime:
                    #print str(var.name)+' existingvar st '+str(var.start_datetime)+' to '+str(new_start_datetime)
                    var._varinfo['start_datetime'] = new_start_datetime
                if new_end_datetime and var.end_datetime != new_end_datetime:
                    #print str(var.name)+' existingvar end '+str(var.end_datetime)+' to '+str(new_end_datetime)
                    var._varinfo['end_datetime'] = new_end_datetime
        #print datetime.utcnow()
   
    def delete_dataset(self, dsname):
        self.datasets.delete_dataset(dsname)

    def add_dataset(self, dataset, name=None, copy=True):
        '''
        Appends a dataset to the SciFile.

        The input dataset will be appended to the DataSetContainer located at SciFile.datasets.
        All shared properties will be connected between the SciFile instance and
        all DataSet instances.

        +------------+---------+----------------------------------------------------+
        | Parameters | Type    | Description                                        |
        +============+=========+====================================================+
        | dataset    | DataSet | A DataSet instance to be appended to self.datasets |
        +------------+---------+----------------------------------------------------+

        +----------+------+----------------------------------------------------------+
        | Keywords | Type | Description                                              |
        +==========+======+==========================================================+
        | name     | str  | A name for the dataset. This will replace dataset.name   |
        |          |      | if copy is True. If copy is False, name will be ignored  |
        |          |      | Default: None                                            |
        +----------+------+----------------------------------------------------------+
        | copy     | bool | A flag indicating whether a fresh copy should be made    |
        |          |      | of the dataset prior to adding it to self.datasets.      |
        |          |      | This generally should be set to `False` unless you are   |
        |          |      | absolutely sure that you will not create leakage between |
        |          |      | objects.                                                 |
        |          |      | Default: True                                            |
        +----------+------+----------------------------------------------------------+
        '''


        if not self.similar(dataset):
            raise SciFileError('Cannot add DataSet to SciFile.  Not similar.')
        if name is None:
            try:
                name = dataset.name
            except AttributeError:
                raise ValueError('Input data must be a DataSet instance.')
        # MLS couldn't figure out why workin gfor viirs and not for
        # himawari. happened that viirs (with separate geolocation 
        # files) didn't have geo file open until AFTER at least one 
        # data file for at least 2 different resolutions was open. 
        # so len(self.dataseets) == 2. variables gets set first (it must)
        # for himawari, and geolocation_variables included for each 
        # channel, so len(self.datasets) ALWAYS == 1 when first 
        # geolocation_variables was set. So it never got set to 
        # BaseContainer, so we try to write to top level 
        # geolocationvariables every time. with the same geolocation_variables
        # names (Latitude , Longitude) every time. Which fails.
        # Have it delete geolocation_variables first, so it checks every 
        # time
        if hasattr(self, '_geolocation_variables'):
            del self._geolocation_variables
        if copy:
            dataset = dataset._create_similar(variables=dataset.variables,
                    geolocation_variables=dataset.geolocation_variables, name=name)

        self.datasets.append(dataset)
        #Ask for variables to test for conflicts
        try:
            self.variables
        except ValueError:
            raise ValueError('Conflicting variable names encountered.  Cannot merge.')

    @property
    def variables(self):
        _variables = BaseContainer(self)
        names = []
        for ds in self.datasets.values():
            names.extend(ds.variables.keys())
            _variables.update(ds.variables)
        #if [k for k,v in Counter(names).items() if v>1]:
        #    raise ValueError('Conflicting variable names encountered in SciFile object.')
        return _variables

    @property
    def geolocation_variables(self):
        # MLS couldn't figure out why workin gfor viirs and not for
        # himawari. happened that viirs (with separate geolocation 
        # files) didn't have geo file open until AFTER at least one 
        # data file for at least 2 different resolutions was open. 
        # so len(self.dataseets) == 2. variables gets set first (it must)
        # for himawari, and geolocation_variables included for each 
        # channel, so len(self.datasets) ALWAYS == 1 when first 
        # geolocation_variables was set. So it never got set to 
        # BaseContainer, so we try to write to top level 
        # geolocationvariables every time. with the same geolocation_variables
        # names (Latitude , Longitude) every time. Which fails.
        # Have it delete geolocation_variables first when calling 
        # add_dataset, so it checks every time
        if len(self.datasets) != 1:
            if not hasattr(self, '_geolocation_variables'):
                self._geolocation_variables = BaseContainer(self)
            _geolocation_variables = self._geolocation_variables
        else:
            _geolocation_variables = self.datasets.values()[0].geolocation_variables
        return _geolocation_variables

    @property
    def runfulldir(self):
        return self._finfo['runfulldir']
    @property
    def dataprovider(self):
        return self._finfo['dataprovider']
    @property
    def source_name(self):
        return self._finfo['source_name']

    # This is used for display in legends, titles, etc. Default to finfo dataprovider
    @property
    def dataprovider_display(self):
        if 'dataprovider_display' in self.metadata['top'].keys() and self.metadata['top']['dataprovider_display']:
            return self.metadata['top']['dataprovider_display']
        else:
            return self._finfo['dataprovider']

    # This is the standard GeoIPS id, used for filenames. Default to finfo source_name 
    @property
    def source_name_product(self):
        if 'source_name_product' in self.metadata['top'].keys() and self.metadata['top']['source_name_product']:
            return self.metadata['top']['source_name_product']
        else:
            return self._finfo['source_name']

    # This is used for display in legends, titles, etc. Default to finfo source_name
    @property
    def source_name_display(self):
        if 'source_name_display' in self.metadata['top'].keys() and self.metadata['top']['source_name_display']:
            return self.metadata['top']['source_name_display']
        else:
            return self._finfo['source_name']

    # This is the standard GeoIPS id, used for filenames. Default to finfo platform_name
    @property
    def platform_name_product(self):
        if 'platform_name_product' in self.metadata['top'].keys() and self.metadata['top']['platform_name_product']:
            return self.metadata['top']['platform_name_product']
        else:
            return self._finfo['platform_name']

    # This is used for display in legends, titles, etc. Default to finfo platform_name
    @property
    def platform_name_display(self):
        if 'platform_name_display' in self.metadata['top'].keys() and self.metadata['top']['platform_name_display']:
            return self.metadata['top']['platform_name_display']
        else:
            return self._finfo['platform_name']
    @property
    def platform_name(self):
        return self._finfo['platform_name']
    @property
    def security_classification(self):
        return self._finfo['security_classification']
    @property
    def start_datetime(self):
        return self._finfo['start_datetime']

    @property
    def mid_datetime(self):
        return self._finfo['start_datetime']+(self._finfo['end_datetime']-self._finfo['start_datetime'])/2

    @property
    def filename_datetime(self):
        return self._finfo['filename_datetime']
    @property
    def end_datetime(self):
        if self._finfo['end_datetime']:
            return self._finfo['end_datetime']
        else:
            return self._finfo['start_datetime']
        
    @property
    def TC_ARCHER_center_lat(self):
        return self._finfo['TC_ARCHER_center_lat']
    @property
    def TC_ARCHER_center_lon(self):
        return self._finfo['TC_ARCHER_center_lon']
    @property
    def TC_ARCHER_intensity(self):
        return self._finfo['TC_ARCHER_intensity']
    @property
    def TC_ARCHER_product_frequency(self):
        return self._finfo['TC_ARCHER_product_frequency']
        
    @property
    def moon_phase_angle(self):
        return self._finfo['moon_phase_angle']
    @property
    def registered(self):
        return self._finfo['registered']

    def sector(self, ad, required_vars=None):
        '''
        Create a new SciFile instance containing the minimum amount of data required
        to cover the input area definition while retaining the original data's projection
        and resolution.

        All DataSets and Variables in the resulting SciFile instance will be rectangularly
        shaped with all data retained in their original lines and samples.  This means that
        there will likely be extra data that are not actually required by the sector around
        the edges of each Variable.  The extra data are required to retain the original data
        projection.
        '''
        #Create a new instance
        new = self.__class__.__new__(self.__class__)
        new.metadata = self.metadata.copy()

        #Loop over the datasets, sector them, and add them to the new instance
        for dsname in self.datasets.keys():
            # If we pass a list of variables, limit to those variables.
            if required_vars and not self.datasets[dsname].has_any_vars(required_vars):
                continue
            newds = self.datasets[dsname].sector(ad,required_vars)
            if not newds:
                log.info('    '+dsname+' Does not intersect sector, skipping!!')
                continue
            # MLS 20150107 ??????????
            #newds._platform_name = self.platform_name
            #newds._sensor_name = self.sensor_name
            #newds._dataprovider = self.dataprovider
            #print ('sector SciFile newds platform_name: '+newds.platform_name)
            new.add_dataset(newds)
        #new._platform_name = self.platform_name
        #new._sensor_name = self.sensor_name
        #new._dataprovider = self.dataprovider
        #new.geostationary = self.geostationary
        #print ('sector SciFile new platform_name: '+new.platform_name)
        return new

    # MLS 20160203 monitor - mem jump at dsname,ds in self.datasets.items() (~.5G)
    #           then at ds.register (~300M)
    # MLS 20160203 pass the required_vars to sf.register - 
    #       this allows us to keep only the full data file
    #       in memory (to avoid in-memory duplicates), 
    #       but only register what we need. required_vars=None
    #       means ALL variables.
    #@profile
    def register(self, ad, interp_method='nearest',required_vars=None,roi=None):
        '''Given an area definition, will register all contained datasets to
        the provided area definition.'''
        if not interp_method:
            interp_method = 'nearest'
        #Create a new instance
        new = self.__class__.__new__(self.__class__)
        new.metadata = self.metadata.copy()
        temp_datasets = {}

        #print_mem_usage('scifbeforeregister',True)
        #Loop over datasets to register
        for dsname in self.datasets.keys():
            # If we pass a list of variables, limit to those variables.
            if required_vars and not self.datasets[dsname].has_any_vars(required_vars):
                continue
            ds = self.datasets[dsname]
            log.info('    Registering ds '+dsname)
            #Don't register if area definitions are equal
            if ds.data_box_definition == ad:
                temp_datasets[dsname] = ds._create_similar(variables=ds.variables,
                        geolocation_variables=ds.geolocation_variables,
                        name=ad.name)
                temp_datasets[dsname].registered = True
            else:
                #Register the dataset
                # MLS 20160203 pass the required_vars to ds.register - 
                #       this allows us to keep only the full data file
                #       in memory (to avoid in-memory duplicates), 
                #       but only register what we need. required_vars=None
                #       means ALL variables.
                temp_datasets[dsname] = ds.register(ad, 
                            interp_method=interp_method,
                            required_vars=required_vars,
                            roi=roi)
        #print_mem_usage('scifafterregister',True)

        #print_mem_usage('scifbeforemerge',True)
        #Loop over datasets again to merge
        reg_ds = None
        for dsname in temp_datasets.keys():
            log.info('    Merging ds '+dsname)
            #If this is the first datset then store it as the new dataset
            if reg_ds is None:
                reg_ds = temp_datasets.pop(dsname)
                reg_ds.name = '__registered__'
            #If this is not the first datset we have registered,
            #   then merge it with the registered dataset
            else:
                reg_ds.merge(temp_datasets.pop(dsname), _do_similar=True)
        #print_mem_usage('scifaftetrmerge',True)
        reg_ds.name = ad.name

        #print_mem_usage('scifbeforeappend',True)
        #Re-add dataset to container
        new.datasets.append(reg_ds)
        #print_mem_usage('scifafterappend',True)

        return new

    def has_night(self, min_zenith=90):
        '''Return True if the file contains locations where SunZenith is less than min_zenith.'''
        #Find the smallest dataset and measure with that
        smallest = None
        for ds in self.datasets.values():
            if smallest is None:
                smallest = ds
            else:
                if ds.size < smallest.size:
                    smallest = ds
        return smallest.has_night(min_zenith=min_zenith)

    def has_day(self, max_zenith=90):
        '''Return True if the file contains locations where SunZenith is greater than max_zenith.'''
        #Find the smallest dataset and measure with that
        smallest = None
        for ds in self.datasets.values():
            if smallest is None:
                smallest = ds
            else:
                if ds.size < smallest.size:
                    smallest = ds
        return smallest.has_day(max_zenith=max_zenith)

    def mask_night(self, min_zenith=90):
        '''Mask data where the solar zenith angle is below min_zenith.'''
        for dsname, ds in self.datasets.items():
            #Mask each dataset
            ds.mask_night(min_zenith=min_zenith)

    def mask_day(self, max_zenith=90):
        '''Mask data where the solar zenith angle is above max_zenith.'''
        for dsname, ds in self.datasets.items():
            #Mask each dataset
            ds.mask_day(max_zenith=max_zenith)

