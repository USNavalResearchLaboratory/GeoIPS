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
from os import getenv
from os import path as p
from os import unlink
from os import makedirs
from os import chmod
try:
    from os import chown
except ImportError:
    print 'os.chown not available'
from os import pardir 
import logging


# Installed Libraries
#from IPython import embed as shell


# GeoIPS Libraries
from geoips.utils.decorators import doc_set
from geoips.utils.log_setup import interactive_log_setup
from .exceptions import PathFormatError
from geoips.utils.plugin_paths import paths as gpaths


log = interactive_log_setup(logging.getLogger(__name__))


def chmodown(path,uid=5029,gid=4959,mod=0o775):
    chmod(path,mod)
    #log.info('chmod '+str(mod)+' '+path)
    #chown(dir,UID,GID)
    # xtuser GID = 4959
    # satuser UID = 5029
    # linux command id tells you these.
    if getenv('USER') == 'satuser':
        try:
            chown(path,uid,gid)
        except NameError:
            log.warning('Chown not defined, skipping')
        #log.info('chown '+str(uid)+' '+str(gid)+' '+path)

class Path(object):
    '''This module takes many of the functions from os.path and puts them into
    an object format where each method of os.path is a method of the Path object.
    Each of these methods will attempt to return an object of the same class as
    self, but will return a base Path object if that is not possible.'''
    #Path separators
    altsep  = p.altsep
    extsep  = p.extsep
    '''Separator used before filename extensions.'''
    pathsep = p.pathsep
    '''Separator used between paths.'''
    sep     = p.sep
    '''Separator used between directory levels.'''

    def __new__(typ, fname, *args, **kwargs):
        obj = object.__new__(typ)
        obj.args = args
        obj.kwargs = kwargs
        return obj
    def __init__(self, fname, *args, **kwargs):
        #This should be _name in order to avoid double initialization of
        #child class instances.
        #If the name attribute is set directly here,
        #child class instances will parse the name twice.
        self._name = fname

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.name)

    def __str__(self):
        return self.name

    def __iter__(self):
        for char in self.name:
            yield char

    def __make_new(self, newstr):
        try:
            return self.__class__(newstr, *self.args, **self.kwargs)
        except PathFormatError:
            return Path(newstr)

    @property
    def name(self):
        return self._name
    @name.setter
    def name(self, val):
        self._name = val

    #######################################
    #str related methods
    #
    # Many of these are probably not needed and can be commented out
    #######################################
    @doc_set(str)
    def capitalize(self):
        return self.__make_new(str.capitalize(self.name))

    @doc_set(str)
    def center(self, width, fillchar=' '):
        return self.__make_new(str.center(self.name, width, fillchar))

    @doc_set(str)
    def count(self, sub, start=None, end=None):
        return self.name.count(sub, start, end)

    #@doc_set(str)
    def decode(self, encoding=None, errors=None):
        '''
        Decode is not implemented for Path objects.

        If this functionality is needed, good luck adding it.
        I've only spent five minutes on this and decided it's not worth my time at the moment.
        Probably need to determine default string encoding from environment somehow.
        '''
        raise NotImplementedError('Decode is not implemented for Path objects.')

    #@doc_set(str)
    def encode(self, encoding=None, errors=None):
        '''
        Encode is not implemented for Path objects.

        If this functionality is needed, good luck adding it.
        I've only spent five minutes on this and decided it's not worth my time at the moment.
        Probably need to determine default string encoding from environment somehow.
        '''
        raise NotImplementedError('Encode is not implemented for Path objects.')

    @doc_set(str)
    def endswith(self, suffix, start=None, end=None):
        return self.name.endswith(suffix, start, end)

    @doc_set(str)
    def expandtabs(self, tabsize=8):
        return self.__make_new(self.name.expandtabs(tabsize))

    @doc_set(str)
    def find(self, sub, start=None, end=None):
        return self.name.find(sub, start, end)

    @doc_set(str)
    def format(self, *args, **kwargs):
        return self.name.format(*args, **kwargs)

    @doc_set(str)
    def index(self, sub, start=None, end=None):
        return self.name.index(sub, start, end)

    @doc_set(str)
    def isalnum(self):
        return self.name.isalnum()

    @doc_set(str)
    def isalpha(self):
        return self.name.isalpha()

    @doc_set(str)
    def isdigit(self):
        return self.name.isdigit()

    @doc_set(str)
    def islower(self):
        return self.name.islower()

    @doc_set(str)
    def isspace(self):
        return self.name.isspace()

    @doc_set(str)
    def istitle(self):
        return self.name.istitle()

    @doc_set(str)
    def isupper(self):
        return self.name.isupper()

    @doc_set(str)
    def join(self, others):
        return self.__make_new(self.name.join(others))

    @doc_set(str)
    def ljust(self, width, fillchar=' '):
        return self.__make_new(str.ljust(self.name, width, fillchar))

    @doc_set(str)
    def lower(self):
        return self.__make_new(self.name.lower())

    @doc_set(str)
    def lstrip(self, chars=None):
        return self.__make_new(self.name.lstrip(chars))

    @doc_set(str)
    def partition(self, sep):
        return tuple(self.__make_new(part) for part in self.name.partition(sep))

    @doc_set(str)
    def replace(self, old, new, count=None):
        if count is None:
            return self.__make_new(self.name.replace(old, new))
        else:
            return self.__make_new(self.name.replace(old, new, count))

    @doc_set(str)
    def rfind(self, sub, start=None, end=None):
        return self.name.rfind(sub, start, end)

    @doc_set(str)
    def rindex(self, sub, start=None, end=None):
        return self.name.rindex(sub, start, end)

    @doc_set(str)
    def rjust(self, width, fillchar=' '):
        return self.__make_new(str.rjust(self.name, width, fillchar))

    @doc_set(str)
    def rpartition(self, sep):
        return tuple(self.__make_new(part) for part in self.name.rpartition(sep))

    @doc_set(str)
    def rsplit(self, sep=None, maxsplit=None):
        if maxsplit is None:
            return [self.__make_new(part) for part in self.name.rsplit(sep)]
        else:
            return [self.__make_new(part) for part in self.name.rsplit(sep, maxsplit)]

    @doc_set(str)
    def rstrip(self, chars=None):
        return self.__make_new(self.name.rstrip(chars))

    @doc_set(str)
    def split(self, sep=None, maxsplit=None):
        if maxsplit is None:
            return [self.__make_new(part) for part in self.name.split(sep)]
        else:
            return [self.__make_new(part) for part in self.name.split(sep, maxsplit)]

    @doc_set(str)
    def splitlines(self, keepends=False):
        return [self.__make_new(part) for part in self.name.splitlines(keepends)]

    @doc_set(str)
    def startswith(self, prefix, start=None, end=None):
        return self.name.startswith(prefix, start, end)

    @doc_set(str)
    def strip(self, chars=None):
        return self.__make_new(self.name.strip(chars))

    @doc_set(str)
    def swapcase(self):
        return self.__make_new(self.name.swapcase())

    @doc_set(str)
    def title(self):
        return self.__make_new(self.name.title())

    @doc_set(str)
    def translate(self, table, deletechars=None):
        if deletechars is None:
            return self.__make_new(self.name.translate(table))
        else:
            return self.__make_new(self.name.translate(table, deletechars))

    @doc_set(str)
    def upper(self):
        return self.__make_new(self.name.upper())

    @doc_set(str)
    def zfill(self, width):
        return self.__make_new(self.name.zfill(width))

    #######################################
    #os.path related methods
    #######################################

    @doc_set(p)
    def abspath(self):
        return self.__make_new(p.abspath(self.name))

    @doc_set(p)
    def basename(self):
        return self.__make_new(p.basename(self.name))

    @doc_set(p)
    def commonprefix(self, others):
        raise NotImplementedError(self.__class__+'.commonprefix not implemented.')

    @doc_set(p)
    def dirname(self):
        return self.__make_new(p.dirname(self.name))

    def chmodownparents(self,path=None):
        if not path:
            path = self.dirname().name
        chmodown(path)
        newpath = p.join(path,pardir)
        ii = 0
        jj=0
        while p.exists(newpath) and p.isdir(newpath):
            #log.info("      *** changing to 0o775 "+' '+str(p.exists(newpath)))
            try:
                ii+=1
                chmodown(newpath)
                newpath = p.join(newpath,pardir)
            except OSError:
                jj+=1
                newpath = p.join(newpath,pardir)
                break
        log.info('      *** changed permissions on '+str(ii)+' '+str(jj)+' parent directories')

    def unlink(self):
        if self.exists():
            try:
                unlink(self.name)
            except OSError:
                if not self.exists():
                    log.info('I guess someone else deleted the file before we had a chance to! '+self.name)
                else:
                    log.error('Failed deleting file: '+self.name)
                    raise
            log.interactive('        *** Deleted file '+self.name)
        else:
            log.info('        *** File does not exist, can not delete: '+self.name)

    def makedirs(self):
        path = self.dirname().name
        if not p.exists(path):
            try:
                makedirs(path)
                chmodown(path)
            except OSError:
                if p.exists(path):
                    log.info('I guess someone else created the directory before we had a chance to! Thanks! '+path)
                    #print('I guess someone else created the directory before we had a chance to! Thanks! '+path)
                else:
                    log.error('Failed creating directory '+path)
                    #print('Failed creating directory '+path)
                    raise
            if not path.startswith(gpaths['HOME']):
                #log.info('        *** Created directory '+path+' changing permissions on all parent directories...')
                # MLS 20170127 Rely on umask for permissions - should be 775 now.
                pass
                #self.chmodownparents()
            else:
                log.info('        *** Created directory '+path+', not changing permissions on all parent directories since path starts with $HOME...')
            return path
        else:
            log.debug('Directory '+path+' already exists, not creating')
            #print('Directory '+path+' already exists, not creating')
            return None 


    @doc_set(p)
    def expanduser(self):
        return self.__make_new(p.expanduser(self.name))

    @doc_set(p)
    def expandvars(self):
        return self.__make_new(p.expandvars(self.name))

    @doc_set(p)
    def normcase(self):
        return self.__make_new(p.normcase(self.name))

    @doc_set(p)
    def normpath(self):
        return self.__make_new(p.normpath(self.name))

    @doc_set(p)
    def realpath(self):
        return self.__make_new(p.realpath(self.name))

    @doc_set(p)
    def relpath(self):
        return self.__make_new(p.relpath(self.name))

    #Base Path object returns
    def splitpath(self):
        head, tail = p.split(self.name)
        head = Path(head)
        tail = Path(tail)
        return (head, tail)

    @doc_set(p)
    def splitdrive(self):
        head, tail = p.splitdrive(self.name)
        head = Path(head)
        tail = Path(tail)
        return (head, tail)

    @doc_set(p)
    def splitext(self):
        head, tail = p.splitext(self.name)
        head = Path(head)
        tail = Path(tail)
        return (head, tail)

    #Time returns
    @doc_set(p)
    def getatime(self):
        return p.getatime(self.name)

    @doc_set(p)
    def getctime(self):
        return p.getctime(self.name)

    @doc_set(p)
    def getmtime(self):
        return p.getmtime(self.name)

    #Number returns
    @doc_set(p)
    def getsize(self):
        return p.getsize(self.name)

    #Boolean returns
    @doc_set(p)
    def exists(self):
        return p.exists(self.name)

    @doc_set(p)
    def isabs(self):
        return p.isabs(self.name)

    @doc_set(p)
    def isdir(self):
        return p.isdir(self.name)

    @doc_set(p)
    def isfile(self):
        return p.isfile(self.name)

    @doc_set(p)
    def islink(self):
        return p.islink(self.name)

    @doc_set(p)
    def ismount(self):
        return p.ismount(self.name)

    @doc_set(p)
    def lexists(self):
        return p.lexists(self.name)

    @doc_set(p)
    def samefile(self, other):
        sname = self.name
        try:
            oname = other.name
        except AttributeError:
            oname = other
        return p.samefile(sname, oname)

    #Odd functions
    @doc_set(p)
    def walk(self, func, arg):
        return p.walk(self, func, arg)

#def commonprefix(names):
#    str_names = [o.name if hasattr(o, 'name') else o for o in names]
#    return p.commonprefix(str_names)
#
#def join(a, *p):
#    pass

