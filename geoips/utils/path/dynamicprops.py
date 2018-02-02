#/bin/env python

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
from functools import partial


class DynamicProps(object):
    def __init__(self):
        pass

    @classmethod
    def _add_property(cls, propname):
        '''Dynamically adds a new property property to FileName class.
        The name of the property is specified by propname.
        Each property recieves partGetter() and partSetter() as their getter and setter.
        This allows for run-time specification of nameformat.
        '''
        #add_property(self, propname)
        getter = partial(cls._part_getter, propname)
        setter = partial(cls._part_setter, propname)
        setattr(cls, propname, property(getter, setter))

    @staticmethod
    def _part_getter(propname, obj):
        '''Getter method for properties specified through _add_property().
        Dynamically sets itself as a getter for the property specified by propname.
        '''
        setattr(obj, '_DYNPROP'+propname, obj.fields[propname])
        return obj.fields[propname]

    @staticmethod
    def _part_setter(propname, obj, val):
        '''Setter method for properties specified through _add_property().
        Dynamically sets itself as a setter for the property specified by propname.
        Sets property in fields dictionary. Don't test property if it's value
        is 'fillvalue' (MLS)
        '''
        if val != obj._fillvalue and hasattr(obj, '_'+propname+'Test'):
            proptest = getattr(obj, '_'+propname+'Test')
            proptest(val)
        if '<' in propname:
            propname = propname.replace('>','').replace('<','')
        if '{' in propname:
            #print 'dynamicprops _part_setter'
            propname,format = propname.split('{',2)
            format = format.replace('}','')
            #print propname+format
        #print 'dynamicprops part_setter propname: '+propname+' val: '+str(val)
        obj.fields[propname] = val
        obj._on_property_change()
        setattr(obj, '_DYNPROP'+propname, val)

    def _on_property_change(self):
        '''Override this to perform an action whenever a property changes.'''
        pass

    def clearattr(self, propname):
        '''Resets an attribute to its fill value.'''
        setattr(self, propname, self.fillvalue)

    def clearall(self):
        for field in self.fields.keys():
            self.clearattr(self, field)
