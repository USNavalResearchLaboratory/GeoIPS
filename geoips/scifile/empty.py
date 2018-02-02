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

__all__ = ['Empty']

class _Final(type):
    '''
    When used, this metaclass will make a class unable to be subclassed.
    If subclassing is attempted a TypeError is raised providing the same
    message as when attempting to subclass types.NoneType.
    '''
    def __new__(cls, name, bases, classdict):
        for b in bases:
            if isinstance(b, _Final):
                raise TypeError("type '%s' is not an acceptable base type" % b.__name__)
        return type.__new__(cls, name, bases, dict(classdict))

class __SingletonType(object):
    '''
    Creates a new singleton with the name Singleton.

    This class should not be used directly.
    It is provided as a convenience for creating new singletons,
    however, it uses shared state and provides no protection
    against improper subclassing.

    Subclass before use and set `__metaclass__` = __Final on the subclass.
    '''
    __slots__ = ()
    __instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls.__instance, cls):
            cls.__instance = object.__new__(cls, *args, **kwargs)
        if cls.__name__[-4:] == 'Type':
            cls.__name =  cls.__name__[0:-4]
        else:
            raise NameError("subclasses of type '%s' must satisfy `cls.__name__[-4:] == 'Type'`")
        return cls.__instance

    def __repr__(self):
        return self.__name

class EmptyType(__SingletonType):
    '''
    Creates a new singleton with the name Empty.
    '''
    __metaclass__ = _Final

Empty = EmptyType()
