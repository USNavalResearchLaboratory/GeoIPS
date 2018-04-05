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

# 20160126 MLS  Pulled all special cases for geostationary out (try to sector at least...)
#               Removed all no mask area definitions (don't need with false corners SwathDefinition)
#               Renamed dataset.area_definition to dataset.data_box_definition (area def specifically
#                   for regions of interest in pyresample lingo)

# Python Standard Libraries
import logging
import math
from operator import mul
import weakref
from datetime import datetime


# Installed Libraries
import numpy as np
from numpy.ma import MaskedArray
from pyresample import kd_tree
from pyresample.geometry import GridDefinition
from IPython import embed as shell
import scipy

# GeoIPS Libraries
from geoips.utils.satellite_info import SatSensorInfo
from .scifileexceptions import SciFileError
from .empty import Empty
from .geometry.boxdefinitions import SwathDefinition
from .geometry.boxdefinitions import PlanarPolygonDefinition


__all__ = ['_empty_finfo', '_empty_dsinfo', '_empty_varinfo',
           'BaseContainer', 'DataSetContainer', 'VariableContainer',
           'DataSet', 'Variable']

log = logging.getLogger(__name__)

# finfo contains data that will be stored at the file level
_empty_finfo = {'source_name': None,
                'platform_name': None,
                'start_datetime': None,
                'end_datetime': None,
                'filename_datetime': None,
                'runfulldir': None,
                'moon_phase_angle': None,
                'dataprovider': None,
                'registered': None}

# dsinfo contains all data that will be stored at the file level plus data to be stored at the datset level
_empty_dsinfo = _empty_finfo.copy()
_empty_dsinfo.update({'shape': None,
                      'tau': None,
                      'footprint_width': None,
                      'footprint_height': None})

# dsinfo contains all data that will be stored at the dataset level plus data to be stored at the
# variable level
_empty_varinfo = _empty_dsinfo.copy()
_empty_varinfo.update({'badval': None,
                       '_nomask': None,
                       'transform_coeff': None})


class BaseContainer(object):
    '''
    A container that acts like a dictionary.
    Previously was ReadOnly, need to be able to remove items.
    '''
    def __init__(self, obj):
        self._obj = weakref.ref(obj)
        self._contents = {}

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._contents)

    def __getitem__(self, key):
        return self._contents[key]

    def __len__(self):
        return len(self._contents)

    def __contains__(self, k):
        return k in self._contents

    @property
    def obj(self):
        return self._obj()

    def delete_item(self, itemname):
        del(self._contents[itemname])

    def get(self, k, d=None):
        return self._contents.get(k, d)

    def has_key(self, k):
        return k in self._contents

    def items(self):
        return self._contents.items()

    def iteritems(self):
        return self._contents.iteritems()

    def iterkeys(self):
        return self._contents.iterkeys()

    def itervalues(self):
        return self._contents.itervalues()

    def keys(self):
        return self._contents.keys()

    def values(self):
        return self._contents.values()

    def append(self, key, val):
        '''
        Append a new key/value pair.  Error on overlapping keys.
        '''
        if key in self._contents:
            raise KeyError("%s already contains the key '%s'" % (self.obj.__class__, key))
        self._force_append(key, val)

    def _force_append(self, key, val):
        '''
        Add a new key/value pair.  Overwrite on overlapping keys.
        '''
        self._contents[key] = val

    def update(self, other):
        '''
        Update from the passed BaseContainer instance.  Error on overlapping keys.
        '''
        if not isinstance(other, BaseContainer):
            raise TypeError("Expected %s got %s." % (BaseContainer, type(other)))
        for key in other._contents.keys():
            self.append(key, other._contents[key])

    def _force_update(self, other):
        '''
        Update from the passed BaseContainer instance.  Overwrite on overlapping keys.
        '''
        self._contents.update(other._contents)


class VariableContainer(BaseContainer):
    '''
    A container whose keys are varible names and whose values are the Variable instances.
    New variables can be added to the container through the append method.
    This will fail if a variable of the same name already exists in the container.
    '''
    def __init__(self, obj, variables=None):
        super(VariableContainer, self).__init__(obj)
        if variables is not None:
            try:
                for var in variables.values():
                    self.append(var)
            except AttributeError:
                ValueError('Keyword "variables" must be a dictionary.')

    def append(self, var):
        '''
        Add a new variable to the container.
        This will fail if a variable with the same name already exists.
        '''
        if var.name in self._contents:
            raise ValueError("%s already contains variable named '%s'" % (self.obj.__class__, var.name))
        self._force_append(var)

    def _force_append(self, var):
        '''
        Set a variable regardless of whether it already exists or not.
        This should generally be avoided.
        '''
        if not isinstance(var, Variable):
            raise TypeError("Expected %s got %s." % (Variable, type(var)))
        # This only connects the Variable with the DataSet
        # Should make a connection between the SciFile instance and the Variable later
        if isinstance(self.obj, DataSet):
            var.dataset = self.obj
        self._contents[var.name] = var

    def _force_update(self, other):
        '''
        Update from the passed VariableContainer instance regardless of overlapping variable names.
        This should generally be avoided.
        '''
        if not isinstance(other, VariableContainer):
            raise TypeError("Expected %s got %s." % (VariableContainer, type(other)))
        self._contents.update(other._contents)
        # This only connects the Variable with the DataSet
        # Should make a connection between the SciFile instance and the Variable later
        if isinstance(self.obj, DataSet):
            for var in self._contents.values():
                var.dataset = self.obj


class DataSetContainer(BaseContainer):
    '''
    A container whose keys are varible names and whose values are the Variable instances.
    New variables can be added to the container through the append method.
    This will fail if a variable of the same name already exists in the container.
    '''
    def __init__(self, obj, datasets=None):
        super(DataSetContainer, self).__init__(obj)
        if datasets is not None:
            try:
                for ds in datasets.values():
                    self.append(ds)
            except AttributeError:
                ValueError('Keyword "datasets" must be a dictionary.')

    def delete_dataset(self, dsname):
        self.delete_item(dsname)

    def append(self, ds, _do_similar=False, copy=False):
        '''
        Add a new dataset to the container.
        This will fail if a dataset with the same name already exists.
        '''
        if not isinstance(ds, DataSet):
            raise TypeError("Expected %s got %s." % (DataSet, type(ds)))
        if ds.name in self._contents:
            ds.merge(self._contents[ds.name], _do_similar=_do_similar, copy=copy)
        # Save this for later.  Will likely want to do this here too
        # ds._optinfo['dataset'] = self.obj
        self._force_append(ds)

    def update(self, other, _do_similar=False, copy=False):
        '''
        Merge two DataSetContainers together to form a single instance.
        Will fail if any dataset with the same name exists.
        '''
        for ds in other.values():
            self.append(ds, _do_similar=_do_similar, copy=copy)

    def _force_append(self, ds):
        '''
        Set a dataset regardless of whether it already exists or not.
        This should generally be avoided.
        '''
        if not isinstance(ds, DataSet):
            raise TypeError("Expected %s got %s." % (DataSet, type(ds)))
        # Save this for later.  Will likely want to do this here too
        # ds._optinfo['dataset'] = self.obj
        self._contents[ds.name] = ds
        # This only connects the DataSet with the SciFile
        ds.scifile = self.obj

    def _force_update(self, other):
        '''
        Upate from teh passed DataSetContainer instance regardless of the overlapping variable names.
        This should generally be avoided.
        '''
        if not isinstance(other, DataSetContainer):
            raise TypeError("Expected %s got %s." % (DataSetContainer, type(other)))
        self._contents.update(other._contents)
        # This only connects the DataSet with the SciFile
        for ds in self._contents.values():
            ds.scifile = self.obj


class DataSet(object):
    def __new__(cls, name, variables=[], geolocation_variables=[],
                scifile=None, copy=True, _dsinfo={}, **kwargs):
        '''
        A class that describes a SciFile DataSet.

        A DataSet is a container for holding similar Variable instances.
        Variables are considered to be "similar" if a specific subset of their attributes
        are equal.  More specifically, "similar" means that all values contained
        in Variable._dsinfo are the same for all Variable instances in the DataSet.
        These values include attributes such as `source_name`, `platform_name`,
        `start_datetime`, and `end_datetime`.  For a full list of attribute names in _dsinfo
        see scifile.containers._empty_dsinfo.

        Similar to Variables, DataSets can also be compared for similarity.
        DataSets are considered to be "similar" if all values contained in DataSet._finfo
        are equal.  For a full listing of these values, see scifile._empty_finfo.
        '''

        obj = object.__new__(cls)
        obj.name = name
        obj.variables = VariableContainer(obj)
        obj.geolocation_variables = VariableContainer(obj)
        # _dsinfo is shared between a DataSet and all of its contained Variables
        # The _dsinfo dictionary holds all Variable attribute values that should
        #    be the same between all Variables in a DataSet.
        # Note that this is the SAME INSTANCE and not just similar dictionaries
        #    so, an update to one Variable within a DataSet is an update to all.
        # Typically the values in here should never actually change except
        #    to go from `None` to something non-`None`.
        if len(_dsinfo) == 0:
            obj._dsinfo = _empty_dsinfo.copy()
        else:
            obj._dsinfo = _dsinfo.copy()
        # _finfo is shared between a DataSet and the SciFile instance that it is
        #    contained in.  This is a subset of _dsinfo and holds all of the
        #    DataSet attribute values that should be shared between all `DataSet`s
        #    contained in a SciFile instance.
        # Note that this is the SAME INSTANCE across an entire SciFile and not
        #    just similar dictionaries so, an update to one DataSet within a
        #    SciFile is an update to all and to all subsequent Variables.
        # Typically the values in here should never actually change except
        #    to go from `None` to something non-`None`.
        obj._dsinfo = _empty_dsinfo.copy()
        for key, val in _dsinfo.items():
            if key in obj._dsinfo:
                obj._dsinfo[key] = val
            else:
                raise SciFileError('Unrecognized dataset attribute in _dsinfo: %s' % key)
        obj._finfo = _empty_finfo.copy()
        for key, val in _dsinfo.items():
            if key in obj._finfo:
                obj._finfo[key] = val

        return obj

    def __init__(self, name, variables=[], geolocation_variables=[], copy=True, **kwargs):
        # We run into some problems when someone passes a single variable instance
        #    rather than a list of Variable instances.
        # This is a crummy looking check, but it works.  If the `shape` attribute is there
        #    then we do not have a list and should fail
        if len(variables) > 0 and (hasattr(variables, '_dsinfo') or not hasattr(variables[0], '_dsinfo')):
            raise ValueError('Keyword `variables` must be a list of Variable instances.')
        for variable in variables:
            self.add_variable(variable, copy=copy)
        if len(geolocation_variables) > 0 and (hasattr(geolocation_variables, '_dsinfo') or not
                                               hasattr(geolocation_variables[0], '_dsinfo')):
            raise ValueError('Keyword `variables` must be a list of Variable instances.')
        for variable in geolocation_variables:
            self.add_geolocation_variable(variable, copy=copy)

    def __getitem__(self, index):
        # Create a new DataSet object
        new = self.__class__(self.name)

        # Initialize containers
        new.variables = VariableContainer(self)
        new.geolocation_variables = VariableContainer(self)
        new.gvars_to_create = []

        # Loop over variables
        for varname in self.variables.keys():
            new.variables.append(self.variables[varname][index])

        # Loop over geolocation variables
        for gvarname in self.geolocation_variables.keys():
            new.geolocation_variables.append(self.geolocation_variables[gvarname][index])

        return new

    def __eq__(self, other):
        if not self.name == other.name:
            return False
        if not isinstance(other, self.__class__):
            return False
        if not self.similar(other):
            return False
        return True

    def __ne__(self, other):
        return not self == other

    # MLS 20160203 in an effort to save memory and stop
    #   storing subset of data separately from full datafile,
    #   begin testing full datafile on existence of variables
    #   as a first test of whether we should run.
    def has_any_vars(self, required_vars):
        dataset_vars = set(self.variables.keys())
        required_vars = set(required_vars)
        # If there are any vars in common between the two,
        # return True
        if required_vars.intersection(dataset_vars):
            return True
        return False

    # MLS 20160203 in an effort to save memory and stop
    #   storing subset of data separately from full datafile,
    #   begin testing full datafile on existence of variables
    #   as a first test of whether we should continue running.
    def has_all_vars(self, required_vars):
        dataset_vars = set(self.variables.keys())
        required_vars = set(required_vars)
        # If all vars in required_vars are in
        # dataset vars, return True.
        # return True
        if required_vars.issubset(dataset_vars):
            return True
        return False

    def similar(self, other):
        '''
        Compare the DataSet instance with either a DataSet or Variable instance to determine similarity.
        Similarity is determined by whether the properties of `self` equal those of `other`.
        '''
        # If self has no variables, then just assume similar
        #    no data means we can't compare.
        if hasattr(self, 'variables') and hasattr(self, 'geolocation_variables'):
            if len(self.variables) == 0 or len(self.geolocation_variables) == 0:
                return True
        # Will loop over all of these attributes and make sure they are either equal or
        #    not set in one or both.
        for attr in self._dsinfo.keys():
            selfattr = getattr(self, attr)
            otherattr = getattr(other, attr)
            if selfattr is not None and otherattr is not None and selfattr != otherattr:
                return False
        return True

    def _create_similar(self, variables=None, geolocation_variables=None, name=None):
        '''
        Create a new DataSet instance where all initial values are the same as the current instance.

        +-----------------------+-------------------+-----------------------------------------------------------+
        | Keywords              | Type              | Description                                               |
        +=======================+===================+===========================================================+
        | variables             | list              | A list or VariableContainer containing Variable instances |
        |                       | or                | to be added to the new DataSet instance. These Variables  |
        |                       | VariableContainer | will be copied, not stored by reference.                  |
        +-----------------------+-------------------+-----------------------------------------------------------+
        | geolocation_variables | list              | A list or VariableContainer containing Variable instances |
        |                       | or                | to be added to the new DataSet instance. These Variables  |
        |                       | VariableContainer | will be copied, not stored by reference.                  |
        +-----------------------+-------------------+-----------------------------------------------------------+
        | name                  | str               | A new name for the DataSet                                |
        +-----------------------+-------------------+-----------------------------------------------------------+
        '''
        name = name if name is not None else self.name
        # Allow variables to be a VariableContainer
        try:
            variables = variables.values()
        except AttributeError:
            pass
        try:
            geolocation_variables = geolocation_variables.values()
        except AttributeError:
            pass
        newobj = self.__class__(name, variables=variables, geolocation_variables=geolocation_variables,
                                _dsinfo=self._dsinfo, _finfo=self._finfo)
        return newobj

    def add_variable(self, data, name=None, copy=True, _force=False):
        '''
        Appends a variable to the DataSet.

        Can accept any ndarray instance.

        If the input data is not a Variable instance, the name keyword must be supplied.

        If the input data is a Variable instance, will copy the instance by default to avoid
            backwards propagaion of variable information.

        If the copy keyword is set to False and the input data is a Variable instance,
            the Variable will be added directly without a copy.  It is recommended that
            this option is only used when reading data directly into the DataSet instance.
            If the same Variable instance is added to two DataSet instances copy=False,
            any changes to the Variable in one DataSet will propagate to the other DataSet.

        Raises a KeyError if a variable of the same name already exists in this DataSet.
        '''
        if not self.similar(data):
            raise SciFileError('Cannot add Variable to DataSet.  Not similar.')
        if name is None:
            try:
                name = data.name
            except AttributeError:
                raise ValueError('Input data must either be a Variable instance or name keyword must be provided.')
        # NOTE:  When adding a new variable in this method, we should try to create a clean variable
        #       with no additional references in order to avoid backward propagation of changes.
        if copy:
            data = data._create_similar(data, name=name)
        if _force:
            self.variables._force_append(data)
        else:
            self.variables.append(data)

    def add_geolocation_variable(self, data, name=None, copy=True, _force=False):
        '''
        Appends a variable to the DataSet.

        Can accept any ndarray instance.

        If the input data is not a Variable instance, the name keyword must be supplied.

        If the input data is a Variable instance, will copy the instance by default to avoid
            backwards propagaion of variable information.

        If the copy keyword is set to False and the input data is a Variable instance,
            the Variable will be added directly without a copy.  It is recommended that
            this option is only used when reading data directly into the DataSet instance.
            If the same Variable instance is added to two DataSet instances copy=False,
            any changes to the Variable in one DataSet will propagate to the other DataSet.

        Raises a KeyError if a variable of the same name already exists in this DataSet.
        '''
        if not self.similar(data):
            raise SciFileError('Cannot add Variable to DataSet.  Not similar.')
        if name is None:
            try:
                name = data.name
            except AttributeError:
                raise ValueError('Input data must either be a Variable instance or name keyword must be provided.')
        # NOTE:  When adding a new variable in this method, we should try to create a clean variable
        #       with no additional references in order to avoid backward propagation of changes.
        if copy:
            data = data._create_similar(data, name=name)
        if _force:
            self.geolocation_variables._force_append(data)
        else:
            self.geolocation_variables.append(data)

    def readall(self):
        '''
        Reads data for all contained variables.
        This will replace all variables and geolocation variables with new Variable instances
            containing data rather than an array of "None".
        '''
        for var in self.variables.values():
            self.variables._force_append(var.get_with_data())

        for gvar in self.geolocation_variables.values():
            self.variables._force_append(var.get_with_data())

    def create_subset(self, variables=[], geolocation_variables=[]):
        '''
        Returns a new instance of DataSet containing copies of the specified variables.
        Variables returned defaults to None.
        Geolocation variables returned defaults to all.
        Both arguments require a list.
        All variables in the new instance are copies of the original variables so
        modification of their data and attributes will not carry to the original variables.

        A KeyError will be raised if a requested variable is not found.
        No error will be raised for missing geolocation variables.
        '''
        cls = self.__class__
        new = cls.__new__(cls, self.name, _dsinfo=self._dsinfo)
        new.name = self.name

        for varname in variables:
            try:
                new.variables.append(self.variables[varname].copy())
            except KeyError:
                # JES: I'm not sure if I like this solution.  I understand the point, though...
                # raise KeyError('No such variable %s in dataset %s' % (varname, self.name))
                log.warning('No such variable %s in dataset %s.  Will not be included in subset.' %
                            (varname, self.name))
                continue

        if len(geolocation_variables) == 0:
            geolocation_variables = self.geolocation_variables.keys()
        for geovarname in geolocation_variables:
            # Don't error for missing geolocation variables
            try:
                new.geolocation_variables.append(self.geolocation_variables[geovarname].copy())
            except KeyError:
                pass
        if not new.variables:
            return None
        else:
            return new

    def write(self, df, variables=None, geolocation_variables=None):
        # Create a group for this dataset
        ds_group = df.create_group(self.name)

        # Add attributes to the group
        for attr in self._dsinfo.keys():
            if attr not in self._finfo.keys():
                val = getattr(self, attr)
                if val is not None:
                    # datetime objects must be handled specially on write and read
                    if attr in ['start_datetime', 'end_datetime']:
                        ds_group.attrs[attr] = val.strftime('%Y%m%d%H%M%S.%f')
                    else:
                        ds_group.attrs[attr] = val

        # Read all of the data for this dataset
        self.readall()

        # Loop over geolocation variables and call their write method
        gvar_group = ds_group.create_group('geolocation')
        for gvarname in self.geolocation_variables.keys():
            if not geolocation_variables or (geolocation_variables and gvarname in geolocation_variables):
                self.geolocation_variables[gvarname].write(gvar_group)

        # Loop over variables and call their write method
        var_group = ds_group.create_group('variables')
        for varname in self.variables.keys():
            if not variables or (variables and varname in variables):
                self.variables[varname].write(var_group)

    # @property
    # def _userblock(self):
    #    if not hasattr(self, '_userblock_'):
    #        self._userblock_ = objectify.Element('dataset', attrib={'name':self.name})

    #        #Write elements for attributes
    #        #Removed for now: scale, offset, units, storage_dtype, footprint_height, footprint_width
    #        for tag in self._dsinfo.keys():
    #            if getattr(self, tag) is not None:
    #                attrelem = objectify.SubElement(self._userblock, tag)
    #                attrelem._setText('dataset')
    #                attrelem.attrib['attribute'] = tag

    #        #Write elements for geolocation variables
    #        for gvar in self.geolocation_variables.values():
    #            gvarelem = gvar._userblock
    #            gvarelem.tag = 'gvar'
    #            self._userblock_.append(gvarelem)

    #        #Write elements for geolocation variables
    #        for var in self.variables.values():
    #            varelem = var._userblock
    #            varelem.tag = 'var'
    #            self._userblock_.append(varelem)
    #    return self._userblock_

    @property
    def mask(self):
        if not hasattr(self, '_mask'):
            self._mask = np.ma.nomask
        return self._mask

    def _set_mask_inplace(self, mask):
        # If we don't have a mask yet, we will need to distribute the mask to the variables
        if self._mask.ndim == 0:
            self._mask = mask
            for var in self.variables.values():
                var._mask = mask
            for var in self.geolocation_variables.values():
                var._mask = mask
        # If we already have a mask, change its values in place
        else:
            self._mask[...] = mask

    # def __get_merged_mask(self):
    #    '''
    #    Combines all masks from the contained variables and geolocation variables
    #    using a logical or, then sets all of the masks from the contained
    #    variables and geolocation variables to the merged mask.

    #    This is a method of making sure that all variables are masked the same.
    #    This should really only need to be called when the dataset is dirty.
    #    '''
    #    if not hasattr(self, '_mask'):
    #        self._mask = False

    #    ###################################################
    #    #Everything below this should be tabbed in if this winds up getting called frequently
    #    #At the moment, it should only get called when __when_dirty is called
    #    #It may be worth just moving this into __when_dirty to avoid confusion
    #    ###################################################

    #    #Loop over vars and gvars to compile complete mask
    #    for var in self.variables.values():
    #        #print 'merge_mask: '+var.name
    #        varmask = var.mask
    #        if varmask is not False:
    #            if self._mask is False:
    #                self._mask = varmask
    #            else:
    #                self._mask = varmask | self._mask
    #    for gvar in self.geolocation_variables.values():
    #        gvarmask = gvar.mask
    #        if gvarmask is not False:
    #            if self._mask is False:
    #                self._mask = gvarmask
    #            else:
    #                self._mask = gvarmask | self._mask
    #    #Loop over vars and gvars again to distribute the mask across all variables
    #    for var in self.variables.values(): var._mask = self._mask
    #    #for gvar in self.geolocation_variables.values(): gvar._mask = self._mask

    # def set_merged_mask(self, mask, replace=False):
    #    '''
    #    Set the mask for the DataSet and all contained variables and geolocation variables.

    #    If called with replace=False, perform logical or with current mask.
    #    If called with replace=True, replace the current mask.
    #    Defaults to replace=False.

    #    ..Warning::  Calling with replace=False may unmask bad values in datasets.
    #    '''
    #    if replace:
    #        self._mask = mask
    #    else:
    #        self._mask = np.logical_or(mask, self._mask)
    #    for var in self.variables.values(): var._mask = self._mask
    #    for gvar in self.geolocation_variables.values(): gvar._mask = self._mask

    # @property
    # def mask(self):
    #    return self._mask

    # def get_mask(self):
    #    '''
    #    Combines all masks from the contained variables and geolocation variables
    #    using a logical or.  Also
    #    '''
    #    pass

    def _dsinfo_prop_getter(self, propname, noval=None):
        '''
        Gets a value from self._dsinfo using propname as the key to _dsinfo.
        If the key is not found, returns the contents of `noval` which defaults to None.
        '''
        try:
            return self._dsinfo[propname]
        except KeyError:
            return noval

    def _dsinfo_prop_setter(self, propname, val):
        self._dsinfo[propname] = val
        if propname in self._finfo:
            self._finfo[propname] = val

    def _dsinfo_prop_deleter(self, propname):
        try:
            self._dsinfo[propname] = None
            if propname in self._finfo:
                self._finfo[propname] = None
        except KeyError:
            pass

    @property
    def runfulldir(self):
        return self._dsinfo_prop_getter('runfulldir')

    @runfulldir.setter
    def runfulldir(self, val):
        self._dsinfo_prop_setter('runfulldir', val)

    @runfulldir.deleter
    def runfulldir(self):
        self._dsinfo_prop_deleter('runfulldir')

    @property
    def dataprovider(self):
        return self._dsinfo_prop_getter('dataprovider')

    @dataprovider.setter
    def dataprovider(self, val):
        self._dsinfo_prop_setter('dataprovider', val)

    @dataprovider.deleter
    def dataprovider(self):
        self._dsinfo_prop_deleter('dataprovider')

    @property
    def source_name(self):
        return self._dsinfo_prop_getter('source_name')

    @source_name.setter
    def source_name(self, val):
        self._dsinfo_prop_setter('source_name', val)

    @source_name.deleter
    def source_name(self):
        self._dsinfo_prop_deleter('source_name')

    @property
    def platform_name(self):
        return self._dsinfo_prop_getter('platform_name')

    @platform_name.setter
    def platform_name(self, val):
        self._dsinfo_prop_setter('platform_name', val)

    @platform_name.deleter
    def platform_name(self):
        self._dsinfo_prop_deleter('platform_name')

    @property
    def sensor_name(self):
        return self._dsinfo_prop_getter('source_name')

    @sensor_name.setter
    def sensor_name(self, val):
        self._dsinfo_prop_setter('source_name', val)

    @sensor_name.deleter
    def sensor_name(self):
        self._dsinfo_prop_deleter('source_name')

    @property
    def shape(self):
        return self._dsinfo_prop_getter('shape')

    @shape.setter
    def shape(self, val):
        self._dsinfo_prop_setter('shape', val)

    @shape.deleter
    def shape(self):
        self._dsinfo_prop_deleter('shape')

    @property
    def size(self):
        if not self.shape:
            return None
        else:
            return reduce(mul, self.shape, 1)

    @property
    def mid_datetime(self):
        return self._dsinfo_prop_getter('start_datetime') + (self._dsinfo_prop_getter('end_datetime') -
                                                             self._dsinfo_prop_getter('start_datetime')) / 2

    @property
    def start_datetime(self):
        return self._dsinfo_prop_getter('start_datetime')

    @start_datetime.setter
    def start_datetime(self, val):
        self._dsinfo_prop_setter('start_datetime', val)

    @start_datetime.deleter
    def start_datetime(self):
        self._dsinfo_prop_deleter('start_datetime')

    @property
    def filename_datetime(self):
        return self._dsinfo_prop_getter('filename_datetime')

    @filename_datetime.setter
    def filename_datetime(self, val):
        self._dsinfo_prop_setter('filename_datetime', val)

    @filename_datetime.deleter
    def filename_datetime(self):
        self._dsinfo_prop_deleter('filename_datetime')

    @property
    def end_datetime(self):
        _end_dt = self._dsinfo_prop_getter('end_datetime')
        if _end_dt is None:
            _end_dt = self._dsinfo_prop_getter('start_datetime')
        return _end_dt

    @end_datetime.setter
    def end_datetime(self, val):
        self._dsinfo_prop_setter('end_datetime', val)

    @end_datetime.deleter
    def end_datetime(self):
        self._dsinfo_prop_deleter('end_datetime')

    @property
    def tau(self):
        return self._dsinfo_prop_getter('tau')

    @tau.setter
    def tau(self, val):
        self._dsinfo_prop_setter('tau', val)

    @tau.deleter
    def tau(self):
        self._dsinfo_prop_deleter('tau')

    @property
    def footprint_height(self):
        return self._dsinfo_prop_getter('footprint_height')

    @footprint_height.setter
    def footprint_height(self, val):
        self._dsinfo_prop_setter('footprint_height', val)

    @footprint_height.deleter
    def footprint_height(self):
        self._dsinfo_prop_deleter('footprint_height')

    @property
    def footprint_width(self):
        return self._dsinfo_prop_getter('footprint_width')

    @footprint_width.setter
    def footprint_width(self, val):
        self._dsinfo_prop_setter('footprint_width', val)

    @footprint_width.deleter
    def footprint_width(self):
        self._dsinfo_prop_deleter('footprint_width')

    @property
    def moon_phase_angle(self):
        return self._dsinfo_prop_getter('moon_phase_angle')

    @moon_phase_angle.setter
    def moon_phase_angle(self, val):
        self._dsinfo_prop_setter('moon_phase_angle', val)

    @moon_phase_angle.deleter
    def moon_phase_angle(self):
        self._dsinfo_prop_deleter('moon_phase_angle')

    @property
    def registered(self):
        return self._dsinfo_prop_getter('registered')

    @registered.setter
    def registered(self, val):
        self._dsinfo_prop_setter('registered', val)

    @registered.deleter
    def registered(self):
        self._dsinfo_prop_deleter('registered')

    @property
    def sourceinfo(self):
        if not hasattr(self, '_sourceinfo'):
            if self.platform_name and self.source_name:
                self._sourceinfo = SatSensorInfo(str(self.platform_name), str(self.source_name))
            else:
                return None
        return self._sourceinfo

    @property
    def geostationary(self):
        if self.sourceinfo is not None:
            return self.sourceinfo.geostationary
        else:
            return False

    @property
    def data_box_definition(self):
        if not hasattr(self, '_data_box_definition'):
            # #Need a third variable to create a mask
            # var = self.variables[self.variables.keys()[0]]
            # if var.empty is True:
            #    var = var.read()
            # If the variable has not yet been read, then read it
            if self.geolocation_variables['Longitude'].empty is True:
                self.geolocation_variables._force_append(self.geolocation_variables['Longitude'].read())
            # If the variable has not yet been read, then read it
            if self.geolocation_variables['Latitude'].empty is True:
                self.geolocation_variables._force_append(self.geolocation_variables['Latitude'].read())
            # mask = self.geolocation_variables['Longitude'].mask | self.geolocation_variables['Latitude'].mask | var.mask
            # self.geolocation_variables['Longitude'].mask = mask
            # self.geolocation_variables['Latitude'].mask = mask
            # Jeremy had added this in his branch for some reason.  It was breaking things
            # (lat/lon out of range I think). so I commented it out. Probably should check
            # with Jeremy.
            # self._data_box_definition = geometry.SwathDefinition(lons=self.geolocation_variables['Longitude'].filled(1.00000000e30),
            #                                                 lats=self.geolocation_variables['Latitude'].filled(1.00000000e30))
            # if self.geostationary:
            #    self._data_box_definition = GeostationaryDefinition(
            #            lons=np.ma.array(self.geolocation_variables['Longitude'], subok=False),
            #            lats=np.ma.array(self.geolocation_variables['Latitude'], subok=False))
            # else:
            #    self._data_box_definition = geometry.SwathDefinition(
            #            lons=np.ma.array(self.geolocation_variables['Longitude'], subok=False),
            #            lats=np.ma.array(self.geolocation_variables['Latitude'], subok=False))
            # This should be the generalized definition for data on a sphere
            # self._data_box_definition = FalseCornersDefinition(

            # MLS 20160223 For now, ahi is the only dataset that uses the planar definition.
            #   everything else is swath based. Eventually if we have more exceptions for
            #   box definition types, we may want to put this in utils/satellite_info.py
            if self.sensor_name == 'abi':
                self._data_box_definition = GridDefinition(
                    lons=np.ma.array(self.geolocation_variables['Longitude'], subok=False),
                    lats=np.ma.array(self.geolocation_variables['Latitude'], subok=False))
            if self.sensor_name == 'ahi':
                self._data_box_definition = PlanarPolygonDefinition(
                    lons=np.ma.array(self.geolocation_variables['Longitude'], subok=False),
                    lats=np.ma.array(self.geolocation_variables['Latitude'], subok=False))
            else:
                self._data_box_definition = SwathDefinition(
                    lons=np.ma.array(self.geolocation_variables['Longitude'], subok=False),
                    lats=np.ma.array(self.geolocation_variables['Latitude'], subok=False))
            self._data_box_definition.name = self.name
        return self._data_box_definition

    def merge(self, other, _do_similar=True, copy=True):
        '''
        Checks to be sure that two DataSets are equal, then merges them together.
        For the time being, equal means they have the same data source and shape.
        In the future, this should be extended to look at dates, times, etc.
        A merged dataset contains the variables from both datasets.

        Note:: This will clear all properties.
        '''
        # print 'DataSet merge'
        # Check for equality
        if _do_similar is False:
            if self != other:
                raise ValueError('DataSets not equal.  Cannot merge.')
        if not self.similar(other):
            raise ValueError('DataSets not similar.  Cannot merge.')
        # Merge containers
        self_vars = set(self.variables.keys())
        other_vars = set(other.variables.keys())
        if len(self_vars.intersection(other_vars)) != 0:
            raise ValueError('Cannot merge DataSets that contain the same variable.')
        else:
            for varname in other.variables.keys():
                self.add_variable(other.variables[varname], copy=copy)
        for gvarname in other.geolocation_variables.keys():
            # Make sure geolocation variables of the same name are similar
            if gvarname in self.geolocation_variables.keys():
                sgvar = self.geolocation_variables[gvarname]
                ogvar = other.geolocation_variables[gvarname]
                failed_test = 'Incompatible geolocation variables found in merge.'
                if sgvar.shape != ogvar.shape:
                    raise ValueError(failed_test)
                # It should not be required to use .data here.  This is due to a numpy bug.
                if sgvar.data.mean() != ogvar.data.mean():
                    raise ValueError(failed_test)
                if sgvar.min() != ogvar.min():
                    raise ValueError(failed_test)
                if sgvar.start_datetime != ogvar.start_datetime:
                    raise ValueError(failed_test)
                if sgvar.filename_datetime != ogvar.filename_datetime:
                    raise ValueError(failed_test)
                if sgvar.end_datetime != ogvar.end_datetime:
                    raise ValueError(failed_test)
            else:
                # print 'DataSet merge before appending to geolocation_variables'
                self.geolocation_variables.append(other.geolocation_variables[gvarname])

        # Clear properties
        # Normally would clear source and shape, but they got checked in the equality
        #   no need to recompute them...
        if hasattr(self, '_data_box_definition'):
            del self._data_box_definition
        if hasattr(self, '_userblock_'):
            del self._userblock_

    # def overlaps(self, ad):
    #    '''Given an area definition, determines whether the data overlaps the defined area.'''
    #    return self._overlaps_area_definition.overlaps(ad)
    def overlaps(self, ad):
        '''Given an area definition, determines whether the data overlaps the defined area.'''
        # NOTE::  This is a modified version of pyresample.geometry.overlaps
        #        This version will automatically attempt to deal with bad
        #        values at the corners of datasets
        # print 'CONTAINERS2 overlaps - calling pyresample overlaps - which '+\
        #        'first tests each sector point against data corners. '+\
        #        ' then tests each data point against sector corners.'
        retval = self.data_box_definition.overlaps(ad)
        # print '    retval from pyresample overlaps: '+str(retval)
        # I think this is handled in pyresample overlaps
        # for corn in ad.corners:
        #    if self.data_box_definition.__contains__(corn):
        #        retval = True
        return retval

    def overlap_rate(self, ad):
        '''Given an area definition, determines what percentage of teh data overlaps the defined area.'''
        return self.data_box_definition.overlap_rate(ad)

    def sector(self, ad, required_vars=None):
        '''
        Create a new DataSet instance containing the minimum amount of data required
        to cover the maximum possible portion of the input area definition while retaining
        the data's projection and resolution.

        All variables in the resulting DataSet instance will be square arrays with all
            data retained in the original order.  This means that there will likely be
            extra data around the edges of each variable that is not actually required
            by the sector.  The extra data are required to retain the original data
            projection.
        '''
        if self.overlaps(ad) is False:
            print 'Nothing overlaps!'
            return None

        intersection = self.data_box_definition.intersection(ad)
        lats = self.geolocation_variables['Latitude']
        lons = self.geolocation_variables['Longitude']

        # area_definition.intersection sometimes returns values > pi (180)
        # this does not work out so well for the > < lat/lons in intersect_corners
        # so move them back down to -180<lon<180
        for corner in intersection:
            if corner.lon > math.pi:
                corner.lon -= 2 * math.pi
            elif corner.lon < -math.pi:
                corner.lon += 2 * math.pi

        # This needs to be done based on sensor resolution rather than arbitrarily set
        #   Should be sensor resolution(km)/(111km/deg)
        #   This refers to the number 0.00337
        # I'm guessing the .00337 referenced above was what 0.1 used to be... That was too restrictive
        # in some cases, so was replaced with 0.1 ?  0.1 is still too restrictive near the poles,
        # so adding in scaling factor up to 0.4 as we get closer to poles.
        intersect_corners = []
        for corner in intersection:
            currcorners = np.ma.where((np.rad2deg(corner.lon)-(0.1+abs(math.sin(corner.lat))*.4) < lons) &
                                         (np.rad2deg(corner.lon)+(0.1+abs(math.sin(corner.lat))*.4) > lons) &
                                         (np.rad2deg(corner.lat)-(0.1+abs(math.sin(corner.lat))*.4) < lats) &
                                         (np.rad2deg(corner.lat)+(0.1+abs(math.sin(corner.lat))*.4) > lats))
            if len(currcorners[0]) and len(currcorners[1]): 
                intersect_corners += [currcorners]
            else:
                # Lame.  I think my planar approximation for AHI didn't work so well... 
                # Need to go +- 5 to find the corner...
                intersect_corners += [np.ma.where((np.rad2deg(corner.lon)-(0.1+abs(math.sin(corner.lat))*.4) < lons) &
                                         (np.rad2deg(corner.lon)+(0.1+abs(math.sin(corner.lat))*.4) > lons) &
                                         (np.rad2deg(corner.lat)-(5.1+abs(math.sin(corner.lat))*.4) < lats) &
                                         (np.rad2deg(corner.lat)+(5.1+abs(math.sin(corner.lat))*.4) > lats))]
        log.info('data_box_definition intersection: '+str(intersection))
        intersect_x, intersect_y = zip(*intersect_corners)
        try:
            min_x = int(min(np.concatenate(intersect_x)))
            max_x = int(max(np.concatenate(intersect_x)))
            min_y = int(min(np.concatenate(intersect_y)))
            max_y = int(max(np.concatenate(intersect_y)))
        except ValueError,resp:
            log.exception(str(resp)+' Too many corners found.')
            raise ValueError(str(resp)+' Too many corners found.')

        # Instantiate new DataSet object
        obj = self.__class__.__new__(self.__class__, self.name)
        # obj._dataprovider = self.dataprovider
        # obj._platform_name = self.platform_name
        # obj._sensor_name = self.sensor_name
        # print('sector DataSet platform_name: '+self.platform_name)

        # Loop over geolocation variables, extract the correct data
        for gvarname in self.geolocation_variables.keys():
            # gvar = self.geolocation_variables[gvarname].sector((min_x, min_y, max_x, max_y))
            gvar = self.geolocation_variables[gvarname][min_x:max_x+1, min_y:max_y+1]
            obj.geolocation_variables.append(gvar)
        # Loop over data variables, extract the correct data
        for varname in self.variables.keys():
            # If we pass a list of variables, limit to those variables.
            if not required_vars or varname in required_vars:
                # var = self.variables[varname].sector((min_x, min_y, max_x, max_y))
                var = self.variables[varname][min_x:max_x+1, min_y:max_y+1]
                obj.variables.append(var)

        return obj

    # MLS 20160203 memory jump at joined=dstack and resample (goes back
    #           down after resample)
    # MLS 20160203 pass the required_vars to ds.register - 
    #       this allows us to keep only the full data file
    #       in memory (to avoid in-memory duplicates), 
    #       but only register what we need. required_vars=None
    #       means ALL variables.
    # @profile
    def register(self, ad, interp_method='nearest',required_vars=None,roi=None):
        '''Given an area definition will register all variables to the defined area.'''
        if not interp_method:
            interp_method = 'nearest'
        # Initialize containers
        if not required_vars:
            required_vars = self.variables.keys()
        varnames = []
        gvarnames = []
        arrays = []

        # print_mem_usage('cont2beforeappend',True)
        # Gather all variables
        for varname in required_vars:
            # If there are multiple datasets, each var won't be in each dataset.
            # only append from the appropriate dataset...
            if self.has_any_vars([varname]):
                varnames.append(varname)
                arrays.append(self.variables[varname])
        # Gather all geolocation variables
        for gvarname in self.geolocation_variables.keys():
            gvarnames.append(gvarname)
            gvar = self.geolocation_variables[gvarname]
            # if gvarname in ['Latitude', 'Longitude']:
            #    gvar = self.geolocation_variables[gvarname]
            #    gvar = gvar._create_similar(gvar, gvar.name)
            #    gvar._mask = np.ma.nomask
            # else:
            #    gvar = self.geolocation_variables[gvarname]
            arrays.append(gvar)
        # print_mem_usage('cont2afterappend',True)

        # Stack all data into single array
        # MLS 20160203 Memory jump after dstack.
        #       wondering if we can do something
        #       to avoid the duplication here (arrays
        #       and joined are the same thing...)
        # print_mem_usage('cont2beforedstack',True)
        joined = np.ma.dstack(arrays)
        # print_mem_usage('cont2afterdstack',True)
        # joined._optinfo['empty'] = False

        # Below is an attempt at forcing pyresample to quit interpolating the edge pixels.
        # This attempt adds an outer layer of masked data the entire way around the array.
        # pyresample should recognize the masked data and not attempt to interpolate past the masked values.
        # This attempt failed because the data dimensions do not match those supplied to create
        #   self.data_box_definition.
        # At this point, I believe there are three solutions:
        #   1) Use something other than pyresample
        #   2) Fix pyresample so it recognizes the edge of the data
        #   3) Recalculate the data_box_definition using the expanded lats and lons in the joined array
        # Option 1 sounds hard.  Option 2 also sounds hard.  Option 3 sounds inefficient.

        # #Create new area definition using expanded lats and lons
        # locs = np.ma.dstack([self.geolocation_variables['Longitude'], self.geolocation_variables['Latitude']])

        # new_slab = np.zeros_like(locs[0,:,:])
        # new_slab = new_slab.reshape(1, new_slab.shape[0], new_slab.shape[1])
        # #Left
        # new_slab[...] = locs[0,:,:]+(locs[0,:,:]-locs[1,:,:])
        # locs = np.ma.vstack((new_slab, locs))
        # #Right
        # new_slab[...] = locs[-1,:,:]+(locs[-1,:,:]-locs[-2,:,:])
        # locs = np.ma.vstack((locs, new_slab))

        # #Top
        # new_slab = np.zeros_like(locs[:,0,:])
        # new_slab[...] = locs[:,0,:]+(locs[:,0,:]-locs[:,1,:])
        # new_slab = new_slab.reshape(new_slab.shape[0], 1, new_slab.shape[1])
        # locs = np.ma.hstack((new_slab, locs))
        # #Bottom
        # new_slab = np.zeros_like(locs[:,0,:])
        # new_slab[...] = locs[:,-1,:]+(locs[:,-1,:]-locs[:,-2,:])
        # new_slab = new_slab.reshape(new_slab.shape[0], 1, new_slab.shape[1])
        # locs = np.ma.hstack((locs, new_slab))
        # data_ad = geometry.SwathDefinition(lons=locs[...,0], lats=locs[...,1])

        # masked_slab = np.ma.expand_dims(np.zeros_like(joined[0,:,:]), 0)
        # masked_slab.mask[...] = True
        # joined = np.ma.vstack((joined, masked_slab))
        # joined = np.ma.vstack((masked_slab, joined))
        # masked_slab = np.ma.expand_dims(np.zeros_like(joined[:,0,:]), 1)
        # masked_slab.mask[...] = True
        # joined = np.ma.hstack((joined, masked_slab))
        # joined = np.ma.hstack((masked_slab, joined))

        # mask = joined.mask
        # if mask is np.ma.nomask:
        #    mask = np.ma.getmaskarray(joined)
        # mask[0,:,:] = True
        # #mask[1,:,:] = True
        # mask[-1,:,:] = True
        # #mask[-2,:,:] = True
        # mask[:,0,:] = True
        # #mask[:,1,:] = True
        # mask[:,-1,:] = True
        # #mask[:,-2,:] = True
        # joined._mask = mask

        # Run registration
        # joined = kd_tree.resample_nearest(data_ad,
        #                                  joined, ad, radius_of_influence=5000,
        #                                  fill_value=None)

        # This should be attached to the scifile instance.  Probably should move sensor_info.py into scifile
        if not roi:
            if 'interpolation_radius_of_influence' in self.scifile.metadata['top'].keys():
                roi = self.scifile.metadata['top']['interpolation_radius_of_influence']
                log.info('        Using READER radius of influence: '+str(roi))
            else:
                try:
                    sensor_info = self.sourceinfo
                    roi = sensor_info.interpolation_radius_of_influence
                    log.info('        Using SATELLITE_INFO radius of influence: '+str(roi))
                # If we are registering a non-sat dataset, SatSensorInfo is not defined, and ROI not defined.
                # so open default SatSensorInfo object (which will have default ROI)
                except (KeyError,AttributeError):
                    # MLS 20150428
                    # should be set to width * 360 / 110 ? or something.
                    # probably need to add this data type to satellite_info (and name satellite_info something else)
                    sensor_info = SatSensorInfo()
                    roi = sensor_info.interpolation_radius_of_influence
                    log.info('        Using DEFAULT SATELLITE_INFO radius of influence: '+str(roi))
        if hasattr(ad, 'pixel_size_x') and hasattr(ad, 'pixel_size_y'):
            if ad.pixel_size_x > roi or ad.pixel_size_y > roi:
                log.info('        Using sector radius of influence: '+str(ad.pixel_size_x)+' or '+str(ad.pixel_size_y)+', not sensor/product: '+str(roi))
                roi = ad.pixel_size_x if ad.pixel_size_x > ad.pixel_size_y else ad.pixel_size_y
        # print_mem_usage('cont2beforeresample',True)
        # MLS 20160203 huge memory usage during resample, but comes back down
        #       to pre-dstack levels immediately after (can be >2x during)
        if interp_method == 'nearest':
            joined = kd_tree.resample_nearest(self.data_box_definition,
                                          # joined, ad, radius_of_influence=sensor_info.interpolation_radius_of_influence,
                                          joined, ad, radius_of_influence=roi,
                                          fill_value=None)

        elif interp_method == 'gauss':
            joined = kd_tree.resample_gauss(self.data_box_definition,
                                            joined, ad, radius_of_influence=roi,
                                            sigmas=[4000]*len(arrays))#, fill_value=None)

        elif interp_method == 'rectbivariatespline':
            lati = self.geolocation_variables['Latitude']
            longi = self.geolocation_variables['Longitude']

            N = joined.shape[2]
            data_lats = lati[:,0]
            data_lons = longi[0,:]
            sector_lons = ad.get_lonlats()[0]
            sector_lats = ad.get_lonlats()[1]
            joined_new = np.ma.zeros((sector_lons.shape[0], sector_lats.shape[1],N))
            # Loop over all the arrays in joined - all data and lat/lons
            for ii in range(N):
                dataj = joined[:,:,ii]
                # interp = scipy.interpolate.interp2d(data_lats, data_lons, dataj.T)
                # Allow for lat/lon or lon/lat data
                try:
                    interp = scipy.interpolate.RectBivariateSpline(data_lons, data_lats, dataj, kx=1, ky=1)
                except TypeError:
                    interp = scipy.interpolate.RectBivariateSpline(data_lons, data_lats, dataj.T, kx=1, ky=1)
                joined_new[:,:,ii]= interp(sector_lons, sector_lats, grid=False)

                # RectBivariateSpline.__call__ DID NOT like the 1D arrays used in the
                # regrid process
                # interp(sector_lons,sector_lats,grid=False)
            joined = joined_new
            # scipy.interpolate.RectBivariateSpline(Longi, Lati,dataj.transpose() )

        elif interp_method == 'zoom':
            joined = scipy.ndimage.zoom(joined,2)

        elif interp_method == 'filter':
            joined = scipy.ndimage.spline_filter(joined)

        elif interp_method == 'interp2d':
            lati = self.geolocation_variables['Latitude']
            longi = self.geolocation_variables['Longitude']

            N = joined.shape[2]
            data_lats = lati[:,0]
            data_lons = longi[0,:]
            sector_lons = ad.get_lonlats()[0]
            sector_lats = ad.get_lonlats()[1]
            joined_new = np.ma.zeros((sector_lons.shape[0], sector_lats.shape[1],N))
            # Loop over all the arrays in joined - all data and lat/lons
            for ii in range(N):
                dataj = joined[:,:,ii]
                # Allow for lat/lon or lon/lat data
                try:
                    interp = scipy.interpolate.interp2d(data_lons, data_lats, dataj)
                except TypeError:
                    interp = scipy.interpolate.interp2d(data_lons, data_lats, dataj.T)
                joined_new[:,:,ii]= interp(sector_lons[0,:], sector_lats[:,0])

            joined = joined_new

        # Map Coordinates require a specific coordinate system
        # elif interp_method == 'mapcoord':
        #    lati = self.geolocation_variables['Latitude']
        #    longi = self.geolocation_variables['Longitude']

        #    N = joined.shape[2]
        #    data_lats = lati[:,0]
        #    data_lons = longi[0,:]
        #    sector_lons = ad.get_lonlats()[0]
        #    sector_lats = ad.get_lonlats()[1]
        #    points = (sector_lats,sector_lons)
        #    joined = scipy.ndimage.map_coordinates(joined,ad.get_lonlats())

        # Regular Grid needs a 3d cartesian grid in order to work.
        # elif interp_method == 'regulargrid':
        #    lati = self.geolocation_variables['Latitude']
        #    longi = self.geolocation_variables['Longitude']

        #    N = joined.shape[2]
        #    data_lats = lati[:,0]
        #    data_lons = longi[0,:]
        #    sector_lons = ad.get_lonlats()[0]
        #    sector_lats = ad.get_lonlats()[1]
        #    joined_new = np.ma.zeros((sector_lons.shape[0], sector_lats.shape[1],N))
        #    # Loop over all the arrays in joined - all data and lat/lons
        #    for ii in range(N):
        #        dataj = joined[:,:,ii]
        #        #interp = scipy.interpolate.interp2d(data_lats, data_lons, dataj.T)
        #        # Allow for lat/lon or lon/lat data
        #        try:
        #            interp = scipy.interpolate.RegularGridInterpolator((data_lons, data_lats), dataj)
        #        except TypeError:
        #            interp = scipy.interpolate.RegularGridInterpolator((data_lons, data_lats), dataj.T)
        #        joined_new[:,:,ii]= interp(sector_lons, sector_lats, grid=False)

        #    joined = joined_new

        # print_mem_usage('cont2afterresample',True)
        # Instantiate new DataSet object
        obj = self.__class__.__new__(self.__class__, self.name)
        # obj.date_format = self.date_format
        # obj.time_format = self.time_format

        # print_mem_usage('cont2beforecreatesimilar',True)
        # Loop over variables and reset their data attributes with the correct data
        for varind in range(len(varnames)):
            varname = varnames[varind]
            var = arrays[varind]._create_similar(joined[:,:,varind])
            if varname != var.name:
                raise ValueError("Variable logic incorrect in register.  Expected %s and got %s." % (varname, var.name))
            obj.variables.append(var)

        # Loop over geolocation variables and reset their data attributes with the correct data
        # Careful with the indecies here.  They are tricky
        for varind in range(len(varnames), len(varnames)+len(gvarnames)):
            gvarind = varind - len(varnames)
            gvarname = gvarnames[gvarind]
            gvar = arrays[varind]._create_similar(joined[:,:,varind])
            if gvarname != gvar.name:
                raise ValueError("Variable logic incorrect in register.  Expected %s and got %s." % (gvarname, gvar.name))
            obj.geolocation_variables.append(gvar)
        # print_mem_usage('cont2aftercreatesimilar',True)

        # Set the area definition to the registeration area definition
        obj._data_box_definition = ad
        obj.registered = True

        return obj

    def has_night(self, min_zenith=90):
        '''Return True if the DataSet contains locations where SunZenith is less than min_zenith.'''
        # Read SunZenith without reading the rest of the variables to save time here
        # Replace SunZenith variable in self.geolocation_variables
        if self.geolocation_variables['SunZenith'].empty:
            self.geolocation_variables._force_append(self.geolocation_variables['SunZenith'].read())

        # Determine if the DataSet contains daytime data
        if np.ma.any(self.geolocation_variables['SunZenith'] > min_zenith):
            return True
        else:
            return False

    def mask_night(self, min_zenith=90):
        '''Mask all variables in the DataSet where SunZenith is less than min_zenith.'''
        # Read SunZenith without reading the rest of the variables to save time here
        # Replace SunZenith variable in self.geolocation_variables
        if self.geolocation_variables['SunZenith'].empty:
            self.geolocation_variables._force_append(self.geolocation_variables['SunZenith'].read())
        # Determine where night and create DataSet level mask
        self._set_mask_inplace(np.ma.make_mask(self.geolocation_variables['SunZenith'] > min_zenith))

    def has_day(self, max_zenith=90):
        '''Return True if the DataSet contains locations where SunZenith is greater than max_zenith.'''
        # Read SunZenith without reading the rest of the variables to save time here
        # Replace SunZenith variable in self.geolocation_variables
        if self.geolocation_variables['SunZenith'].empty:
            self.geolocation_variables._force_append(self.geolocation_variables['SunZenith'].read())

        # Determine if the DataSet contains daytime data
        if np.ma.any(self.geolocation_variables['SunZenith'] < max_zenith):
            return True
        else:
            return False

    def mask_day(self, max_zenith=90):
        '''Mask all variables in the DataSet where SunZenith is greater than max_zenith.'''
        # Read SunZenith without reading the rest of the variables to save time here
        # Replace SunZenith variable in self.geolocation_variables
        if self.geolocation_variables['SunZenith'].empty:
            self.geolocation_variables._force_append(self.geolocation_variables['SunZenith'].read())
        # Determine where day and create DataSet level mask
        self._set_mask_inplace(np.ma.make_mask(self.geolocation_variables['SunZenith'] < max_zenith))

    @property
    def scifile(self):
        return self._scifile()
    @scifile.setter
    def scifile(self, val):
        if val is None:
            # Attempt to avoid leakage
            self._finfo = self._finfo.copy()
            self._scifile = None
        else:
            if val.similar(self):
                # Merge _finfo together for the scifile and the dataset
                for key in val._finfo.keys():
                    if val._finfo[key] is None and self._finfo[key] is not None:
                        val._finfo[key] = self._finfo[key]
                self._scifile = weakref.ref(val)
                self._finfo = val._finfo
            else:
                log.warning('dataset.scifile Not similar')
                for attr in self._finfo.keys():
                    print '  dataset.scifile self: '+' '+str(attr)+' '+str(getattr(self,attr))
                    print '  dataset.scifile ds:   '+' '+str(attr)+' '+str(getattr(val,attr))+' '+val.name
                    for var in val.variables.keys():
                        print '  dataset.scifile var:  '+' '+str(attr)+' '+str(getattr(val.variables[var],attr))+' '+var
                    for gvar in val.geolocation_variables.keys():
                        print '  Variable.dataset gvar:  '+' '+str(attr)+' '+str(getattr(val.geolocation_variables[gvar],attr))+' '+gvar
                raise SciFileError('Cannot set `scifile` attribute on DataSet.  Not similar.')

    @property
    def dataset_name(self):
        return self.dataset.name


# _empty_dsinfo = {'name': Empty, 'units':Empty, 'badval':Empty, 'storage_dtype':Empty,
#                   'scale':Empty, 'offset':Empty, 'start_date':Empty, 'end_date':Empty,
#                   'start_time':Empty, 'end_time':Empty, 'empty':Empty, 'xml_element':Empty,
#                   'footprint_height':None,'footprint_width':None,'moon_phase_angle':None,
#                   'time_format':Empty, 'date_format':Empty, 'source_name':Empty, 'dataset':Empty,
#                   'platform_name':Empty,'datafile':Empty, '_combined_mask':np.ma.nomask, '_stored_mask':Empty,
#                   '_corners':Empty, 'tau':Empty, '_calculate':Empty,
#                  }

class Variable(MaskedArray):
    _empty_optinfo = {'name':Empty, 'empty':Empty, '_combined_mask':np.ma.nomask, '_stored_mask':Empty}
    def __new__(cls, name, data=None, reader=None, shape=None, dtype=None, dataset=None, _varinfo={},
            _nomask=False, **kwargs):

        # Break keywords out of kwargs
        # Once we've figured out all of the keywords, we should put them in the signature
        # dtype = kwargs['dtype'] if kwargs.has_key('dtype') else None
        hard_mask = kwargs['hard_mask'] if kwargs.has_key('dtype') else True
        # date_format = kwargs['date_format'] if kwargs.has_key('date_format') else '%Y%m%d'
        # time_format = kwargs['time_format'] if kwargs.has_key('time_format') else '%H%M%S'

        # Variable.size and Variable.shape will be overridden below
        #   and will make use of Variable._dat_shape and Variable._dat_size only when
        #   the Variable.data is not Empty.
        # When Variable.data is Empty, we must have other methods for obtaining shape
        #   and size.  See the shape and size properties below.
        # If you are confused about this, please see how numpy.ma.MaskedArray.shape
        #   and numpy.ma.MaskedArray.size work.  Understanding those will help here.
        cls._dat_shape = MaskedArray.shape
        cls._dat_size = MaskedArray.size
        cls._dat_dtype = MaskedArray.dtype

        # Instantiate the object using MaskedArray's __new__
        obj = super(Variable, cls).__new__(cls, data=data, dtype=np.dtype(dtype), hard_mask=hard_mask)

        # If we explicitly passed data, warn that it will supercede any reader, shape, and dtype keyword
        if data is not None:
            if (reader is not None) or (shape is not None) or (dtype is not None):
                log.warning('Recieved explicit data for Variable instance.  '+
                            '`reader`, `shape`, and `dtype` keywords will be ignored.'
                           )
        # If we did not explicity pass data, then check for a reader, shape, and dtype.
        # If any of these keywords were not set, then error.
        else:
            # if reader is None:
            #    raise SciFileError('Either an explicit data array must be supplied or '+
            #            'a function must be supplied to the reader keyword.'
            #            )
            if (shape is None) or (dtype is None):
                raise SciFileError('If the `reader` keyword is supplied to Variable '+
                        'the `shape` and `dtype` keywords must also be supplied.'
                        )
            # These attributes are used in the `Variable.read` method, the `Variable.shape`
            #   property, and the `Variable.dtype` property, respectively.
            # They are used when data has not yet been read from the data file to provide
            #   data information as required.
            else:
                obj._given_reader = reader
                obj._given_shape = shape
                obj._given_dtype = dtype

        # If we don't have data yet, then set empty to True.
        # The real data are always stored in obj._data if we have real data.
        if not obj._data.shape:
            obj._optinfo['empty'] = True
        else:
            obj._optinfo['empty'] = False

        obj._optinfo['name'] = name
        obj._optinfo['badval'] = kwargs['badval'] if kwargs.has_key('badval') else None


        # Set up _dsinfo and _mask
        # MLS If we passed _nomask, don't try to set the mask.
        # beware of issues with this down the line - we put this 
        # in when the RSCAT reader was failing when passing _nomask=True
        # when it did not have a mask to copy.  There may be more 
        # reliances on having a mask later in the processing. 
        if not _nomask:
            obj._mask = data.mask.copy()
        obj._varinfo = _empty_varinfo.copy()
        for key, val in _varinfo.items():
            if obj._varinfo.has_key(key):
                obj._varinfo[key] = val
            else:
                # Just don't include non-required variables, don't fail
                pass
                # raise SciFileError('Unrecognized variable attribute in _varinfo: %s' % key)
        obj._dsinfo = _empty_dsinfo.copy()
        for key, val in _varinfo.items():
            if obj._dsinfo.has_key(key):
                obj._dsinfo[key] = val

        # The mask is shared between variables by default.  Setting this forces a variable to
        #   ALWAYS return np.ma.nomask regardless.
        # Useful to avoid masking geolocation variables
        # May be better to just find a better way to handle things in register.
        # register requires unmasked lats and lons
        if _nomask or (_varinfo.has_key('nomask') and _varinfo['nomask']):
            obj._varinfo['_nomask'] = True
        else:
            obj._varinfo['_nomask'] = False

        return obj

    # def __init__(self, name, **kwargs):
    #    super(Variable, self).__init__(**kwargs)

    def __array_finalize__(self, obj):
        super(Variable, self).__array_finalize__(obj)

    def _update_from(self, obj):
        '''
        Copies some attributes of obj to self.
        '''
        # Make sure we maintain our class
        if obj is not None and isinstance(obj, np.ndarray):
            _baseclass = type(obj)
        else:
            _baseclass = np.ndarray

        # We need to copy the _optinfo to avoid backward propagation
        # _basedict is deprecated according to numpy discussion as of 2008
        # It is kept around for backwards compatability
        _optinfo = {}
        _optinfo.update(getattr(obj, '_optinfo', {}))
        _optinfo.update(getattr(obj, '_basedict', {}))
        if not isinstance(obj, Variable):
            _optinfo.update(self._empty_optinfo)
        if not isinstance(obj, MaskedArray):
            _optinfo.update(getattr(obj, '__dict__', {}))

        # We need to copy _attrinfo to avoid backward propagation
        # Unlike _optinfo, _attrinfo is not used in the parent MaskedArray
        #   and is unique to Variable objects.
        # This allows for easier copying without polluting the MaskedArray infrastructure
        _varinfo = {}
        _varinfo.update(getattr(obj, '_varinfo', {}))
        _dsinfo = {}
        _dsinfo.update(getattr(obj, '_dsinfo', {}))
        _finfo = {}
        _finfo.update(getattr(obj, '_finfo', {}))
        _dict = dict(_fill_value=getattr(obj, '_fill_value', None),
                     _hardmask=getattr(obj, '_hardmask', False),
                     _sharedmask=getattr(obj, '_sharedmask', False),
                     _isfield=getattr(obj, '_isfield', False),
                     _baseclass=getattr(obj, '_baseclass', _baseclass),
                     _optinfo=_optinfo,
                     _basedict=_optinfo,
                     _varinfo=_varinfo,
                     _dsinfo=_dsinfo,
                     _finfo=_finfo,
                    )
        self.__dict__.update(_dict)
        self.__dict__.update(_optinfo)

    def write(self, group):
        badval = -999.9
        varobj = group.create_dataset(self.name, data=self.filled(fill_value=badval))
        varobj.attrs['badval'] = badval
        for attr in self._varinfo.keys():
            if attr not in self._dsinfo.keys() and attr not in self._finfo.keys():
                val = getattr(self, attr)
                if val is not None:
                    # datetime objects must be handled specially on write and read
                    if isinstance(val, datetime):
                        varobj.attrs[attr] = val.strftime('%Y%m%d%H%M%S.%f')
                    else:
                        varobj.attrs[attr] = val

    # @property
    # def _userblock(self):
    #    varelem = objectify.Element('var', attrib={'name':self.name})
    #    varpath = os.path.join('/', self.dataset.name, self.name)
    #    dataelem = objectify.SubElement(varelem, 'data')
    #    dataelem._setText(varpath)

        # #Removed for now: scale, offset, units, storage_dtype, footprint_height, footprint_width
        # for tag in ['source_name', 'platform_name', 'start_datetime','filename_datetime','end_datetime', 'badval',
        #            'moon_phase_angle']:
        #    if getattr(self, tag) is not None:
        #        attrelem = objectify.SubElement(varelem, tag)
        #        attrelem._setText(varpath)
        #        attrelem.attrib['attribute'] = tag
    #    return varelem

    # MLS 20160203 Haven't profiled this yet.
    # @profile
    def _create_similar(self, data=None, name=None):
        '''
        Create a new instance of the class where all initial values are the same
        as the current instance, but where the data have been replaced with the intput
        data.
        '''
        if not isinstance(data, np.ma.MaskedArray):
            data = np.ma.array(data)
        # The way name is handled here makes me think that name should not be in _optinfo.
        name = name if name is not None else self.name
        newobj = self.__class__(name, data=data)
        # Something is funny with how shape is stored.  We've gotta do this to get the correct shape.
        shape = newobj.shape
        newobj._update_from(self)
        newobj._varinfo['shape'] = shape
        newobj._dsinfo['shape'] = shape
        if name is not None:
            newobj._optinfo['name'] = name
        return newobj


    # ################################################################
    #
    # Data and data manipulation functions and properties
    #
    # ################################################################
    def __getitem__(self, index):
        # The _empty attribute indicates whether we have read data into the array yet.
        # If _empty is True, then we have not yet read data and need to do so
        #   since __getitem__ acts on the data.
        # Reading the data will always return a new object.
        if self.empty is True:
            return self._create_similar(data=self._given_reader(index))
        else:
            return self._create_similar(super(Variable, self).__getitem__(index))

    def get_with_data(self, index=None):
        '''Return a new instance whose data field is not Empty.'''
        if self.empty:
            return self._create_similar(data=self._given_reader(index))
        else:
            return self._create_similar(data=self)

    def similar(self, other):
        '''
        Compare the Variable with either a DataSet or Variable instance to determine similarity.
        Similarity is determined when the contents of _dsinfo in `self` is equal to the same in `other`.
        Values that are either set to `Empty` or `None` in either or both objects will be ignored.
        '''
        # If other appears to be a DataSet and it has no variables, then just assume similar
        #   no data means we can't compare.
        if hasattr(other, 'variables') and hasattr(other, 'geolocation_variables'):
            if len(other.variables) == 0 or len(other.geolocation_variables) == 0:
                return True
        # Will loop over all of these attributes and make sure they are either equal or
        #   not set in one or both
        # print 'other.name: '+other.name
        for attr in self._dsinfo.keys():
            # print 'Variable other: '+other.name+' '+str(attr)+' '+str(getattr(other,attr))
            # print 'Variable self: '+self.name+' '+str(attr)+' '+str(getattr(self,attr))
            selfattr = getattr(self, attr)
            otherattr = getattr(other, attr)
            if selfattr is not None and otherattr is not None and selfattr != otherattr:
                return False
        # print 'shouldnt return False'
        return True

    # ################################################################
    #
    # Mask manipulation functions and properties
    #
    # The mask for Variable instances can be set prior to reading the data.
    #   If this is done, the mask information is stored in self._stored_mask.
    #   Typically, this is done when another Variable in the same DataSet has
    #   been read and a mask has been applied.  Since masks are shared across
    #   Variables from the same DataSet, we store a temporary mask in _stored_mask
    #   and allow the mask to accumulate until the data are read.
    #
    # ################################################################
    @property
    def _mask(self):
        # This is useful for geolocation variables where we don't want to carry the mask
        if hasattr(self, '_nomask') and self._nomask:
            return np.ma.nomask
        if (not self.empty) and (self._stored_mask is not np.ma.nomask):
            self._combined_mask = self._combined_mask | self._stored_mask
            self._stored_mask = np.ma.nomask
        return self._combined_mask
    @_mask.setter
    def _mask(self, val):
        if self.empty:
            self._stored_mask = val
        else:
            if self._stored_mask is not np.ma.nomask:
                self._combined_mask = self._stored_mask | val
                self._stored_mask = np.ma.nomask
            # elif self._combined_mask is not Empty:
            #    self._combined_mask = self._combined_mask | val
            else:
                self._combined_mask = val
        return self._combined_mask

    @property
    def _combined_mask(self):
        if not hasattr(self, '_combined_mask_'):
            self._combined_mask_ = np.ma.nomask
        return self._combined_mask_
    @_combined_mask.setter
    def _combined_mask(self, val):
        self._combined_mask_ = val

    @property
    def _stored_mask(self):
        if not hasattr(self, '_stored_mask_'):
            self._stored_mask_ = np.ma.nomask
        return self._stored_mask_
    @_stored_mask.setter
    def _stored_mask(self, val):
        self._stored_mask_ = val

    # ################################################################
    #
    # Size and shape functions and properties
    #
    # ################################################################
    # Should probably error if the shape changes after read.
    # The following functions allow a Variable object to have shape and size while remaining empty.
    # This allows a user to pass a reader for the variable along with its shape rather than
    #   requiring an explicit data array in order to delay reading data and reduce I/O.
    def __get_shape(self):
        try:
            return self._given_shape
        except AttributeError:
            raise SciFileError('Unable to get shape for current variable.  '+
                    'May need to implement method of getting shape from the data file.')
    @property
    def shape(self):
        # This gets a little weird.
        # self._dat_shape has been set equal to np.ma.MaskedArray.shape so that it will always
        #   accurately reflect the shape of the current array.
        # If, however, the array is empty, we still want to return the appropriate shape for the
        #   data that could be read into the instance.
        # In order to do this, we allow for a given shape or corners to specify our shape.
        # Additionally, setting self._varinfo['shape'] each time this is called will make sure that
        #   the shape is accurately and constnatly shared with the self.dataset.
        if not self._dat_shape:
            if not hasattr(self, '_corners'):
                self._varinfo['shape'] = tuple(self.__get_shape())
            else:
                self._varinfo['shape'] = (self._corners[2]-self._corners[0], self._corners[3]-self._corners[1])
        else:
            self._varinfo['shape'] = self._dat_shape
        # Set this, too, so that we are sure to share with the dataset
        self._dsinfo['shape'] = self._varinfo['shape']
        return self._varinfo['shape']

    @property
    def size(self):
        if not self._dat_shape:
            if not self.shape:
                return 0
            else:
                return reduce(mul, self.shape, 1)
        else:
            return self._dat_size

    # ################################################################
    #
    # Variable state information properties
    #
    # ################################################################

    # Variable specific properties are stored in _optinfo
    @property
    def empty(self):
        return self._optinfo['empty']
    @empty.setter
    def empty(self, val):
        if not isinstance(val, bool):
            raise ValueError('Attribute "%s" expected %s.  Got %s.' % ('empty', bool, type(val)))
        self._optinfo['empty'] = val

    @property
    def badval(self):
        return self._varinfo['badval']

    @property
    def transform_coeff(self):
        return self._varinfo['transform_coeff']

    @property
    def name(self):
        return self._optinfo['name']

    # Properties to be shared with the dataset instance are stored in _dsinfo
    @property
    def dataprovider(self):
        return self._dsinfo['dataprovider']

    @property
    def runfulldir(self):
        return self._dsinfo['runfulldir']

    @property
    def source_name(self):
        return self._dsinfo['source_name']

    @property
    def platform_name(self):
        return self._dsinfo['platform_name']

    # Probably Variable specific.  Should be in _optinfo if needed.
    # @property
    # def data_provider(self):
    #    return self._dsinfo['data_provider']

    @property
    def mid_datetime(self):
        return self._dsinfo['start_datetime']+(self._dsinfo['end_datetime']-self._dsinfo['start_datetime'])/2

    @property
    def start_datetime(self):
        return self._dsinfo['start_datetime']

    @property
    def filename_datetime(self):
        return self._dsinfo['filename_datetime']

    @property
    def end_datetime(self):
        if self._dsinfo['end_datetime']:
            return self._dsinfo['end_datetime']
        else:
            return self._dsinfo['start_datetime']

    @property
    def tau(self):
        return self._dsinfo['tau']

    @property
    def footprint_height(self):
        return self._dsinfo['footprint_height']

    @property
    def footprint_width(self):
        return self._dsinfo['footprint_width']

    @property
    def moon_phase_angle(self):
        return self._dsinfo['moon_phase_angle']

    @property
    def _nomask(self):
        return self._varinfo['_nomask']

    @property
    def registered(self):
        return self._dsinfo['registered']

    # @property
    # def badval(self):
    #    if self._optinfo['badval'] is Empty:
    #        try:
    #            self._optinfo['badval'] = self.__read_attr_value('badval')
    #        except AttributeError:
    #            self._optinfo['badval'] = None
    #    if self._optinfo['badval'] is not None:
    #        try:
    #            self._optinfo['badval'] = float(self._optinfo['badval'])
    #        except ValueError:
    #            raise SciFileError('Attribute `badval` must be a number.  Got %s.' % self._optinfo['badval'])
    #    return self._optinfo['badval']
    # @badval.setter
    # def badval(self, val):
    #    if val is None:
    #        self._optinfo['badval'] = None
    #    else:
    #        self._optinfo['badval'] = np.array([val], dtype=self.storage_dtype)
    #        try:
    #            self._optinfo['badval'] = float(self._optinfo['badval'])
    #        except ValueError:
    #            raise SciFileError('Attribute badval must be a number.  Got %s line.' % 
    #                               (self._optinfo['badval']))

    # @property
    # def storage_dtype(self):
    #    if self._optinfo['storage_dtype'] is Empty:
    #        storage_dtype = self.__read_attr_value('storage_dtype')
    #        if isinstance(storage_dtype, np.ndarray):
    #            storage_dtype = storage_dtype[0]
    #        self._optinfo['storage_dtype'] = self.__convert_dtype_to_numpy(storage_dtype)
    #    return self._optinfo['storage_dtype']
    # @storage_dtype.setter
    # def storage_dtype(self, val):
    #    self._optinfo['storage_dtype'] = np.dtype(val)

    @property
    def _corners(self):
        '''This is used to store slice information if the variable is empty
        and will be used when the variable is eventually read to memory to limit
        the data read.'''
        return self._optinfo['_corners']

    @property
    def dataset(self):
        return self._dataset()
    @dataset.setter
    def dataset(self, val):
        if val is None:
            # Attempt to avoid leakage
            self._dsinfo = self._dsinfo.copy()
            self._mask = self._mask.copy()
            self._dataset = None
        else:
            if val.similar(self):
                # Merge _dsinfo together for the dataset and the variable
                for key in val._dsinfo.keys():
                    if val._dsinfo[key] is None and self._dsinfo[key] is not None:
                        val._dsinfo[key] = self._dsinfo[key]
                        # Store what we need in _finfo as well
                        if key in val._finfo:
                            val._finfo[key] = getattr(self, key)
                self._dataset = weakref.ref(val)
                self._dsinfo = val._dsinfo
                # Share the mask
                val._set_mask_inplace(self._mask | val.mask)
                self._mask = val._mask
            else:
                for attr in self._dsinfo.keys():
                    print '  Variable.dataset self: '+' '+str(attr)+' '+str(getattr(self,attr))
                    print '  Variable.dataset ds:   '+' '+str(attr)+' '+str(getattr(val,attr))+' '+val.name
                    for var in val.variables.keys():
                        print '  Variable.dataset var:  '+' '+str(attr)+' '+str(getattr(val.variables[var],attr))+' '+var
                    for gvar in val.geolocation_variables.keys():
                        print '  Variable.dataset gvar:  '+' '+str(attr)+' '+str(getattr(val.geolocation_variables[gvar],attr))+' '+gvar
                raise SciFileError('Cannot set `dataset` attribute on Variable.  Not similar.')

    @property
    def dataset_name(self):
        return self.dataset.name
