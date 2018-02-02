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
from inspect import getcallargs
from weakref import WeakKeyDictionary
from functools import partial


# Installed Libraries
from IPython import embed as shell


class ClassFactory(object):
    '''NOTE:  Should test to be sure this is self cleaning.
              Classes should disappear when out of scope.
              Need to set up to work for more than just _FileNameBase.
    '''
    def __init__(self):
        #Maintain a dictionary of weak references to each previously instantiated class
        #See the weakref module
        self.weak_class_cache = WeakKeyDictionary()
    def make(self, typ, *args, **kwargs):
        # MLS 20150513 Stop reusing classes... Might need to readdress 
        # this later...
#        #Try grabbing a previously instantiated class
#        existing_class = self.get_existing_class(typ, *args, **kwargs)
#        #print 'classfactory.make existing_class: '+str(existing_class)
#        try:
#            #existing_class always returns None if there is no matching objects
#            #   including if the object simply has been garbage collected
#            #This will always raise a TypeError if unable to instantiate using
#            #   a previous class
#            obj = existing_class(*args, **kwargs)
#        except TypeError:
#            #If no previously instantiated class, then create a new one
#            typname = self.get_unique_name(typ)
#            cls = type(typname, (typ._dynamic_base, typ), {})
#            self.weak_class_cache[cls] = getcallargs(cls.__new__, type, *args, **kwargs)
#            obj = cls(*args, **kwargs)
#        return obj
        typname = self.get_unique_name(typ)
        cls = type(typname, (typ._dynamic_base, typ), {})
        self.weak_class_cache[cls] = getcallargs(cls.__new__, type, *args, **kwargs)
        obj = cls(*args, **kwargs)
        return obj
    def get_existing_class(self, typ, *args, **kwargs):
        '''If a class with exactly the same call (other than the path argument) exists
        then return that class.  Otherwise return None.
        '''
        currcall = getcallargs(typ.__new__, type, *args, **kwargs)
        #print 'classfactory.get_existing_class currcall: '+str(currcall)
        for key in self.weak_class_cache.keys():
            if equiv_calls(currcall, self.weak_class_cache[key], skipkeys=['path', 'name']):
                return key#(*args, **kwargs)
        return None
    def get_unique_name(self, typ):
        '''Compares typ.__name__ against the keys of self.weak_class_cache
        to find the first unique name available 
        (i.e. does not exist in self.weak_class_cache.keys()).

        If a class of the current name already exists, increment the number at the end.

        Assuming FileName objects have been instantiated 100 times with different calls, 
        a list of FileName class names would look like:
            FileName, FileName_1, FileName_2, ..., FileName_97, FileName_98, FileName_99
        '''
        typ_basename, typ_num = self.split_classname(typ.__name__)
        #Find similar classnames for previously instantiated classes
        similar = [cn.__name__ for cn in self.weak_class_cache.keys() if typ_basename in cn.__name__]
        similar.sort()
        #Make new classname whose number is one above the current greatest
        if len(similar) > 0:
            sim_basename, sim_num = self.split_classname(similar[-1])
            typname = sim_basename + '_' + str(int(sim_num) + 1)
        else:
            typname = typ_basename
        return typname
    @staticmethod
    def split_classname(clsname):
        '''Split a class name into name and number.'''
        #Split the class name on underscores
        cls_parts = clsname.split('_')
        #Retrieve the class number (if it is there)
        cls_num = cls_parts[-1]
        #If clsname had a number, then create the cls_basename (clsname without the number)
        #   otherwise just use clsname and set the number to zero
        if cls_num.isdigit():
            return '_'.join(cls_parts[0:-1]), cls_num
        else:
            return clsname, 0

def equiv_calls(d1, d2, skipkeys=[]):
    d1_parts = set([':'.join([key, str(val)]) for key, val in d1.items() if key not in skipkeys])
    d2_parts = set([':'.join([key, str(val)]) for key, val in d2.items() if key not in skipkeys])
    #print 'classfactory.equiv_calls d1_parts, d2_parts: \n'+str(d1_parts)+'\n'+str(d2_parts)
    return d1_parts == d2_parts
