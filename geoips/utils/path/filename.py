#!/usr/bin/env python

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


# 20150630  Mindy  allow bz2
#                    allow for checking for no %Y if only date (and not time) 
#                       set on datetime_fields
#                       This is going to need to be fixed at some point to 
#                       allow for %y !! (otherwise   
#                       will break reprocessing old data that uses %y. 
#                       something does, can't recall off
#                       the top of my head)
#                   add send_to_TAPE_ARCHIVE_DIR
#                   allow using %! at the end of a datetime string to ignore 
#                       characters (one %! for each character to ignore - ONLY 
#                       WORKS AT THE END, NOT THE MIDDLE!)
# 20160330  Mindy  If %S dtX field > 59, set dtvals used in strptime to 59.
#                   MeghaTropiques Saphir data stopped because one of them had
#                   seconds of 60. 

# Python Standard Libraries
import os
import re
import logging
import shutil
from glob import glob
from copy import copy
from datetime import datetime,timedelta
import filecmp


# Installed Libraries
from IPython import embed as shell


# GeoIPS Libraries
from .path import Path
from .dynamicprops import DynamicProps
from .classfactory import ClassFactory
from .exceptions import PathFormatError

log = logging.getLogger(__name__)

#__all__ = ['FileName', 'FilePath', 'SingleDir']#, 'SingleDir']
__all__ = ['FileName']#, 'SingleDir']

class_factory = ClassFactory()


def wildcard_datetime_fields(dt,datetime_wildcards,datetime_fields):
    ''' datetime_wildcards is {} for no wildcarding.
        Pass something like { '%H':'*','%M':'*','%S':'*'} to wildcard 
            hours, minutes, seconds in the filename. 
        datetime_fields is a dictionary of the datetime fields on the object
            ie, {'date':'%Y%m%d','time':'%H%M%S'}
            this comes directly from self.datetime_fields on the object 
        Returns a dictionary of the actual wildcarded datetime fields (or just straight values)
            ie, {'date':'201608*','time':'***' } or no wildcards {'date':'20160824','time':'062315'}
        '''
    retval = {}
    #print datetime_fields
    #print datetime_wildcards
    #print dt
    for dt_field in datetime_fields.keys():

        new_format = datetime_fields[dt_field]

        for dt_wildcard in datetime_wildcards.keys():
            # If current field contains %H, replace the %H part with *
            if dt_wildcard in new_format:
                # Yields something like %Y%m%d*%M
                new_format = new_format.replace(dt_wildcard,datetime_wildcards[dt_wildcard])
                #print new_format

        # Use original datetime - wildfn won't have a valid datetime
        #    if more than one datetime field have *'s
        # Yields something like 20160621** 
        new_dtstr = dt.strftime(new_format)
        #print new_dtstr
        # Set the new wildcarded datetime field (will not have valid datetime now!!)
        #self.datetime_fields[dt_field]=new_dtstr
        retval[dt_field] = dt.strftime(new_dtstr)
        #print retval
    return retval

def daterange(start_datetime,end_datetime,hours=False):
    if hours: 
        # Didn't get if +1 if like 20 min from 4:50 to 5:10
        for n in range(int((end_datetime-start_datetime).total_seconds() / (60*60) + 2)):
            yield start_datetime + timedelta(hours=n)
    else:
        for n in range(int((end_datetime-start_datetime).days + 1)):
            yield start_datetime + timedelta(n)

def get_fieldname(fieldname,keepformat=False):
    if '<' in fieldname:
        fieldname = fieldname.replace('<','').replace('>','')
        # If we pass a fieldname without <> but with {}, return just the name portion
        if '{' in fieldname and not keepformat:
            fieldname = fieldname.split('{',2)[0]
    else:
        # force variable field elements to be surrounded by <>
        fieldname = None
    return fieldname

class _FileNameBase(Path, DynamicProps):
    '''
    The base class for FileName objects.

    .. warning::
        Objects of this class should never be instantiated directly.
        Multiple instances of direct instantiation with different
        arguments will lead to pollution of the objects with erroneous 
        property attributes.

    This class dynamically builds new FileName type objects 
    whose properties are determined by the nameformat argument.
    Each field name from the nameformat argument is appended to
    the class as a property whose getter and setter methods are
    `DynamicProps._part_getter` and `DynamicProps._part_setter`, 
    respectively.
    '''
    
    def __new__(typ, path, nameformat, fieldsep='.', fillvalue='x', 
                 pathnameformat=None, pathfieldsep=None, pathfillvalue=None,noextension=False):
        '''

        +------------+-----------------------------------------------------------------------+
        | Parameters |                                                                       |
        +============+=======================================================================+
        | typ        | Type of the calling class.                                            |
        +------------+-----------------------------------------------------------------------+
        | nameformat | Format string defining how the filename will be formatted.            |
        |            | Each field is separated by fieldsep.                                  |
        |            | Should not contain the file extension.                                |
        |            | The text between each delimiter will be added to the class            |
        |            | as a property.                                                        |
        +------------+-----------------------------------------------------------------------+

        +----------------+-------------------------------------------------------------------------------+
        | Keywords       |                                                                               |
        +================+===============================================================================+
        | fieldsep       | String to use as the delimeter between fields in nameformat and path.         |
        +----------------+-------------------------------------------------------------------------------+
        | fillvalue      | String used to fill missing values in filename.                               |
        +----------------+-------------------------------------------------------------------------------+
        | pathnameformat | Format string to use when instantiating self.dirname,                         |
        |                | which is a FilePath instance.                                                 |
        +----------------+-------------------------------------------------------------------------------+
        | pathfieldsep   | String to use as the delimeter between fields in directories.                 |
        |                | Mainly used by SingleDir instance to find fields in each directory name.      |
        +----------------+-------------------------------------------------------------------------------+
        | pathfillvalue  | Fill value to be used for missing values in FilePath and SingleDir instances. |
        +----------------+-------------------------------------------------------------------------------+

        '''
        path = str(path)
        #Instantiate new object
        #print '_FileNameBase typ '+str(typ)
        obj = Path.__new__(typ,
                           path,
                           nameformat,
                           fieldsep=fieldsep,
                           fillvalue=fillvalue,
                           pathnameformat=pathnameformat,
                           pathfieldsep=pathfieldsep,
                           pathfillvalue=pathfillvalue,
                           noextension=noextension
                          )
        #print '_FileNameBase __new__ obj.__class__ '+str(obj.__class__)
        obj.__class__._nameformat = nameformat           #String determining filename format
        obj.__class__._fieldsep = fieldsep               #String to use as fieldsep in filename
        obj.__class__._fillvalue = fillvalue             #String to use as fill value for empty fields
        obj.__class__._noextension = noextension
        #Keyword args for FilePath classes
        obj.__class__._pathkwargs = {
                                     'nameformat': pathnameformat,
                                     'fieldsep':   pathfieldsep or fieldsep,
                                     'fillvalue':  pathfillvalue or fillvalue,
                                    }
        obj.__initialized = False

        # MLS use getter/setter for obj.ext, so can change dynamically. Use _ext here
        #print '_FileNameBase noextension: '+str(noextension)
        if noextension:
            obj._ext = ''     #File extension
        else:
            base,obj._ext = os.path.splitext(path)     #File extension
            if obj._ext == '.gz':
                obj._ext = os.path.splitext(base)[1]+'.gz'
            if obj._ext == '.bz2':
                obj._ext = os.path.splitext(base)[1]+'.bz2'
            # Do not store '.' with ext. Chop off first .
            obj._ext = obj._ext[1:]
            #print obj._ext
        obj.fields = {'ext':obj._ext}                         #Dictionary of file name fields
        obj.datetime_fields = {}
        obj._datetime = None

        #shell()
        obj.name = path
        if path:
            obj._origdirname = os.path.dirname(str(path))
        else:
            obj._origdirname = None

        obj.__initialized = True
        obj._on_property_change()

        return obj

    # MLS allow calling with no arguments to create an empty FileName object
    def __init__(self, path=None, nameformat=None, fieldsep='.', fillvalue='x', 
                 pathnameformat=None, pathfieldsep=None, pathfillvalue=None,noextension=False):
        if path:
            self._origdirname = os.path.dirname(str(path))
        else:
            self._origdirname = None
        #print '_FileNameBase __init__ self: '+str(self)
        #print 'super(_FileNameBase,self): '+str(super(_FileNameBase,self))
        super(_FileNameBase, self).__init__(fname=self.name, nameformat=nameformat, fieldsep=fieldsep,
                fillvalue=fillvalue, pathnameformat=pathnameformat, pathfieldsep=pathfieldsep,
                pathfillvalue=pathfillvalue,noextension=noextension)

    def _on_property_change(self):
        if self.__initialized is True:
            #print 'starting _on_property_change'
            # self.ext stores '.' when exists, otherwise empty string
            extstr = ''
            if self.ext:
                extstr = '.'+self.ext
            #print '    _on_property_change setting self._basename in _on_property_change'
            self._basename = make_new_name(self._nameformat, self._fieldsep, self.fields,fillvalue=self._fillvalue)+extstr
            #print self.fields
            #print self.datetime_fields
            #print '    _on_property_change setting self._dirname in _on_property_change pathnameformat: '+str(self.get_pathnameformat())
            self._dirname = make_new_name(self.get_pathnameformat(), self.get_pathfieldsep(), self.fields,dt=self.datetime,ext=self.ext,pathfillvalue=self.get_pathfillvalue())
            if not self._dirname:
                self._dirname = self._origdirname

            #print self.fields
            #print self.datetime_fields

            dtfmts = ''
            dtvals = ''
            hasyear = False
            badfield = False
            if hasattr(self,'date') and self.date != self.get_fillvalue() and 'date' in self.datetime_fields.keys():
                if '%Y' in self.datetime_fields['date']:
                    hasyear = True
                dtfmts += self.datetime_fields['date']
                dtvals += self.date
            if hasattr(self,'time') and self.time != self.get_fillvalue() and 'time' in self.datetime_fields.keys():
                if '%Y' in self.datetime_fields['time']:
                    hasyear = True
                dtfmts += self.datetime_fields['time']
                dtvals += self.time
            # Allow for additional datetime fields - named dt0, dt1, etc
            for ii in range(0,6):
                if hasattr(self,'dt'+str(ii)) and getattr(self,'dt'+str(ii)) != self.get_fillvalue() and 'dt'+str(ii) in self.datetime_fields.keys():
                    dtfmts += self.datetime_fields['dt'+str(ii)]
                    if '%Y' in self.datetime_fields['dt'+str(ii)]:
                        hasyear = True
                    # MeghaTropiques Saphir data sometimes had seconds of 60, failed with strptime.
                    # This will NOT work if a file has more than %S or %M for a single field.
                    # If that case comes up, the logic must be adjusted.
                    if '%S' == self.datetime_fields['dt'+str(ii)] and int(getattr(self,'dt'+str(ii))) > 59:
                        #print 'dt'+str(ii)+' > 59 '+str(dtfmts)+' '+str(dtvals)
                        #badfield = True
                        dtvals += "59"
                    # MeghaTropiques Saphir data sometimes had MINUTES of 60, failed with strptime.
                    # This will NOT work if a file has more than %S or %M for a single field.
                    # If that case comes up, the logic must be adjusted.
                    elif '%M' == self.datetime_fields['dt'+str(ii)] and int(getattr(self,'dt'+str(ii))) > 59:
                        #print 'dt'+str(ii)+' > 59 '+str(dtfmts)+' '+str(dtvals)
                        #badfield = True
                        dtvals += "59"
                    else:
                        dtvals += getattr(self,'dt'+str(ii))
            # If %Y is not defined, figure out what the date is based on current date
            # MLS THIS WILL PROBABLY FAIL FOR %y defined if trying to reprocess old data!
            if not hasyear:
                testdatetime = datetime.strptime(dtvals,dtfmts)
                currYYYY = int(datetime.utcnow().strftime('%Y'))
                currJJJ = int(datetime.utcnow().strftime('%j'))
                fileJJJ = testdatetime.strftime('%j')
                if int(currJJJ) < 20 and int(fileJJJ) > 330:
                    YYYY = currYYYY - 1
                else:
                    YYYY = currYYYY
                dtfmts += '%Y'
                dtvals += str(YYYY)

            #print str(dtfmts)+str(dtvals)
            if dtfmts and dtvals:
                #print str(dtfmts)+str(dtvals)
                # If there are extra characters at the beginning and/OR end of a datetime string, use %! to ignore them
                # one at a time (this ONLY works at the beginning and/OR end of the string - will have to figure out 
                # different logic to make it work in the middle. Should be pretty straightforward to implement that...)
                if "%!" in dtfmts:
                    ii = 0
                    while dtfmts[-(ii*2+1)] == '!':
                        # print ''
                        # print -(ii*2+1)
                        # print dtfmts
                        # print dtvals
                        # print dtfmts[-(ii*2+1)]
                        # print dtvals[:-1]
                        # Only removes trailing data in string! not in middle!!
                        if dtfmts[-(ii*2+1)] == '!':
                            dtvals = dtvals[:-1]
                        ii += 1
                    ii = 0
                    while dtfmts[ii*2+1] == '!':
                        # print ''
                        # print ii*2+1
                        # print dtfmts
                        # print dtvals
                        # print dtfmts[(ii*2+1)]
                        # print dtvals[1:]
                        # Only removes leading data in string! not in middle!!
                        if dtfmts[ii*2+1] == '!':
                            dtvals = dtvals[1:]
                        ii += 1
                    dtfmts = dtfmts.replace('%!','')
                try:
                    #if badfield:
                    #    print str(dtfmts)+' '+str(dtvals)
                    self.datetime = datetime.strptime(dtvals,dtfmts)
                except ValueError:
                    self.datetime = None
            else:
                self.datetime = None

            #self._dirname = os.path.dirname(self.name)
            self._name = os.path.join(self._dirname, self._basename)
            #print 'leaving _on_property_change self._name: '+str(self._name)

    def set_datetime_str(self,dt=None,datetime_wildcards={},datetime_fields={}):
        ''' datetime_wildcards is {} for no wildcarding.
                Pass something like { '%H':'*','%M':'*','%S':'*'} to wildcard 
                hours, minutes, seconds in the filename. 
            datetime_fields is a dictionary of the datetime fields on the object
                ie, {'date':'%Y%m%d','time':'%H%M%S'}
                this typically comes directly from self.datetime_fields on the object 
            Returns a dictionary of the actual wildcarded datetime fields (or just straight values)
                ie, {'date':'201608*','time':'***' } or no wildcards {'date':'20160824','time':'062315'}
        '''
        if not dt:
            dt = self.datetime
        if not dt:
            return self.get_fillvalue(),self.get_fillvalue()
        if not datetime_fields:
            datetime_fields = self.datetime_fields
        retval = []
        from geoips.utils.path.filename import wildcard_datetime_fields

        return wildcard_datetime_fields(dt,datetime_wildcards,datetime_fields)


    @property
    def datetime(self):
        '''Getter for self.datetime'''
        return self._datetime

    @datetime.setter
    def datetime(self,val):
        self._datetime = val

    def send_to_TAPE_ARCHIVE_DIR(self,archivedir=os.getenv('TAPE_ARCHIVE_DIR')):
        '''Pass alternate archivedir if file is not backed up to TAPE_ARCHIVE_DIR
        ie, scat data gets backed up to TAPE_ARCHIVE_DIR_SCAT, so would be
        called as 
        scatfile.send_to_TAPE_ARCHIVE_DIR(archivedir=os.getenv('TAPE_ARCHIVE_DIR_SCAT'))'''
        finalfilename = archivedir+'/'+os.path.basename(self.name)
        finalgzfilename = archivedir+'/'+os.path.basename(self.name)+'.gz'
        if not os.path.exists(archivedir):
            os.makedirs(archivedir)
        log.info('    cp -p '+self.name+' '+finalfilename)
        shutil.copy2(self.name,finalfilename)
        if not os.path.isfile(finalgzfilename):
            cmd = '    gzip -f '+finalfilename
            log.info(cmd)
            os.system(cmd)
        else:
            log.error('File already existed, not gzipping again '+finalgzfilename)

    @staticmethod
    def is_concurrent_with(startdt,other_startdt,enddt=None,other_enddt=None,maxtimediff=timedelta(hours=0),contained_in_other=False):
        if (enddt == None and other_enddt != None):
            #log.debug('startdt: '+str(startdt)+' other_startdt: '+str(other_startdt)+' other_enddt: '+str(other_enddt))
            if abs(startdt-other_startdt) < maxtimediff \
                or abs(startdt-other_enddt) < maxtimediff \
                or (startdt >= other_startdt and startdt <= other_enddt):
                return True

        if (enddt != None and other_enddt == None):
            if abs(other_startdt-startdt) < maxtimediff \
                or abs(other_startdt-enddt) < maxtimediff \
                or (other_startdt >= startdt and other_startdt <= enddt):
                return True

        if (enddt == None and other_enddt == None):
            #print 'enddt and other_enddt none'
            if abs(startdt - other_startdt) < maxtimediff:
                return True

        if contained_in_other == False:
            if (enddt != None and other_enddt != None):
                timediff1 = (abs(enddt - other_startdt))
                timediff2 = (abs(startdt - other_enddt))
                if timediff1 < maxtimediff or timediff2 < maxtimediff: 
                    return True
                if enddt <= other_startdt or other_enddt <= startdt:
                    return False
                else:
                    return True
        else:
            #print ('contained_in_other=True, must be contained in other')
            if (enddt != None and other_enddt != None):
                #print ('enddt: '+str(enddt)+' < other_enddt: '+str(other_enddt))
                #print ('startdt: '+str(startdt)+' > other_startdt: '+str(other_startdt))
                if enddt <= other_enddt and startdt >= other_startdt:
                    #print ('PASSED!')
                    #print ('enddt: '+str(enddt)+' < other_enddt: '+str(other_enddt))
                    #print ('startdt: '+str(startdt)+' > other_startdt: '+str(other_startdt))
                    return True

        return False

    def get_nameformat(self):
        return self._nameformat
    def get_fieldsep(self):
        return self._fieldsep
    def get_fillvalue(self):
        return self._fillvalue
    def get_pathnameformat(self):
        return self._pathkwargs['nameformat']
    def get_pathfieldsep(self):
        return self._pathkwargs['fieldsep']
    def get_pathfillvalue(self):
        return self._pathkwargs['fillvalue']
    def set_pathnameformat(self,val):
        self._pathkwargs['nameformat'] = val
        self._on_property_change()
    def set_pathfieldsep(self,val):
        self._pathkwargs['fieldsep'] = val
        self._on_property_change()
    def set_pathfillvalue(self,val):
        self._pathkwargs['fillvalue'] = val
        self._on_property_change()

    # MLS Allow changing file extension dynamically as well
    @property
    def ext(self):
        '''Getter for self.ext.'''
        return self._ext
    @ext.setter
    def ext(self, val):
        '''Setter for ext attribute.'''
        #Update name attribute with input value.
        self._ext = val
        self._on_property_change()

    @property
    def name(self):
        '''Getter for self.name.'''
        return self._name
    @name.setter
    def name(self, val):
        '''Setter for name attribute.'''
        #Update name attribute with input value.
        #print 'starting name in _FileNameBase: noextension: '+str(self._noextension)+' val: '+str(val)
        self._name = val
        #Split off the extension prior to parsing, allows a different field separator than
        # '.', and still have ext (and not have it lumped in with last field)
        if self._noextension:
            name = val
            ext = ''
        else:
            name, ext = os.path.splitext(val)
            if ext == '.gz':
                name = os.path.splitext(name)[0]
            if ext == '.bz2':
                name = os.path.splitext(name)[0]
        #shell()
        #Parse input value to set fields attribute dictionary.
        if self._nameformat is not None:
            self.__parse(name)
        #print 'leaving name in _FileNameBase'

    def basename(self):
        return self.__class__(self._basename, *self.args, **self.kwargs)

    def __parse(self, name):
        '''Parses input file name.
        For each field, adds a property to the FileName class.
        '''
        #print 'in __parse for FileNameBase name: '+name
        #print '    __parse self.fields: '+str(self.fields)
        #print '    __parse name: '+name
        fields = parse(os.path.basename(name), self._nameformat, self._fieldsep, self._fillvalue,self._ext)

        #Loop over the fields and add them as properties
        for fieldname, fieldval in fields.items():
            fieldname = get_fieldname(fieldname)
            #print '    __parse fieldname '+fieldname
            if not ( fieldname ):
                continue
            self.__class__._add_property(fieldname)
            setattr(self, fieldname, fieldval)

        # If we specified a pathnameformat, and there is a directory specified, parse it
        if self.get_pathnameformat() and os.path.dirname(name):
            dirfields = parse(os.path.dirname(name),self.get_pathnameformat(),self.get_pathfieldsep(),self.get_pathfillvalue())
            for dirfieldname,dirfieldval in dirfields.items():
                if not hasattr(self,dirfieldname): 
                    # Add dirfieldname/dirfieldval into fields, so we pull
                    # time fields from paths too... BEFORE we reset dirfieldname
                    # to just the name without formatting info
                    # This is only used for DISPLAY of datetime as strings 
                    # in directory / file name string. Any field that contains
                    # {} with a valid datetime format string can be displayed 
                    # using the datetime stored with the filename. The datetime
                    # is actually set using the hard coded fields listed in 
                    # _on_property_change (date, time, dt0,dt1,dt2,dt3,dt4,dt5,dt6)
                    # Those fields will actually set the datetime.
                    fields[dirfieldname] = dirfieldval
                    dirfieldname = get_fieldname(dirfieldname)
                    #print '    __parse dirfieldname '+str(dirfieldname)
                    if not ( dirfieldname ):
                        continue
                    self.__class__._add_property(dirfieldname)
                    setattr(self, dirfieldname, dirfieldval)
            #print '    __parse dirfields: '+str(dirfields)
        #print '    __parse self.fields: '+str(self.fields)
        #print '    __parse fields:      '+str(fields)

        # get all the datetime formatted fields ( with {} in field name)
        # should this go within the for loop above?
        dtvals,dtformats = self.get_datetime_formats(fields,self._fillvalue)

#        if dtformats:
#            self.__class__._add_property('datetime')
#            setattr(self,'datetime',datetime.strptime(dtvals,dtformats))
#        else:
#            self.__class__._add_property('datetime')
#            setattr(self,'datetime',None)

    #def from_dict(self, namedict, nameformat, fieldsep='.', fillvalue='_'):
    #    '''Constructs a filename.
    #    namedict   - a dictionary containing key value pairs where the keys are the names
    #                 of fields in the filename and the values are the values of those fields
    #    nameformat - A string describing the format of the filename.
    #                 Consists of the names of each field separated by the fieldsep.
    #    fieldsep  - The field separator as a string.
    #    fillvalue  - Value to be placed in empty fields.
    #    '''
    #    return FileName(fieldsep.join([namedict[part] or fillvalue for part in nameformat.split(fieldsep)]),
    #                    nameformat,
    #                    fieldsep,
    #                    fillvalue
    #                   )
    
    def get_datetime_formats(self,fields,fillval):
        # MLS if {} in name of property, assume it is a date/time format string
        #print 'in get_datetime_formats'
        #print fields
        dtvals = ''
        dtformats = ''
        for fieldname, fieldval in fields.items():
            fieldname = get_fieldname(fieldname,keepformat=True)
            if fieldname and '{' in fieldname:
                #print '    parse date/time'+fieldname+' '+fieldval
                fieldname,format = fieldname.split('{',2)
                format = format.replace('}','')
                self.datetime_fields[fieldname] = format
                if fieldval != fillval:
                    dtvals+=fieldval
                    dtformats+=format
        return dtvals,dtformats

class FileName(object):
    '''
    Provides an interface to easily create and modify filenames with specific formats.
    While this was developed for GeoIPS, this should easily be extendable to any application.
    `FileName` objects must be instantiated with the string `path` and `nameformat` arguments.

    The `path` argument defines the relative or fully-qualified path to a file,
    while the `nameformat` argument defines the format of the filename and the names of each 
    field within the filename.

    The fields of the filename are delimited by the string `fieldsep` keyword which defaults to '.'.
    Each field in `fieldsep` is attached to the object as a property, 
    allowing easy access to each field from the top level of the object.
    Any fields containing missing values will be filled using the string `fillvalue` keyword.

    Example in the standard product file format for GeoIPS::
        >>> foo = FileName(
                           'NorthAmerica-CONUS-West/x-California-x/True-Color/viirs/20120101.000000.viirs.npp.True-Color.California.covg100p0.png',
                           nameformat='date.time.satellite.sensor.product.sector.extra',
                           fieldsep='.',
                           fillvalue='x',
                           pathnameformat='continent-country-area/subarea-state-city/product/sensor',
                           pathfieldsep='-',
                           pathfillvalue='x',
                           noextension=False
                          )
        >>> foo.name
        'NorthAmerica-CONUS-West/x-California-x/True-Color/viirs/20120101.000000.viirs.npp.True-Color.California.covg100p0.png'
        >>> foo.continent
        NorthAmerica
        >>> foo.dirname
        'NorthAmerica-CONUS-West/x-California-x/True-Color/viirs/'
        >>> foo.basename
        '20120101.000000.viirs.npp.True-Color.California.covg100p0.png'
    '''
    _dynamic_base = _FileNameBase
    def __new__(typ, path, nameformat, fieldsep='.', fillvalue='x',
                pathnameformat=None, pathfieldsep=None, pathfillvalue=None,noextension=False):

        #print '\n\n\nFileName new noextension: '+str(noextension)
        #print 'FileName before class_factory.make: '+str(typ)

        obj = class_factory.make(typ, path, nameformat, fieldsep, fillvalue,
                                 pathnameformat, pathfieldsep, pathfillvalue,noextension=noextension)
        #print 'FileName after class_factory.make: obj: '+str(obj)
        return obj

#############################################################
### get_other_files, find_files_in_range, and find_all_files should go in filename.py
### pull out list_other_files, check_dirs_for_files, open_new, and set_wildcards in individual subclasses
#############################################################
    @staticmethod
    def get_other_files(obj,all=False,num_minutes=2,trim=False,extra=None,quiet=False, duplicates=True):
        '''trim=True trims to an odd number of granules 
            (need for viirs rdr converter)
        all=True returns all files including original, 
        all=False does not include the original filename
        duplicates=True includes files with the same time 
        duplicates=False only includes the latest file when more than one with the same time
        num_minutes specifies how many minutes around the given filename
            should be matched
        extra specifies if there are certain strings that must be in the 
            extra field in order to be a match.
        base_dirs appeared to be unused, so I removed it...
            (using datafilename.check_dirs_for_files, which uses 
            sensorinfo, instead of passing base_dirs)
            called as:
                datafilename.list_other_files
                calls filename.get_other_files
                    calls datafilename.set_wildcards
                    calls datafilename.check_dirs_for_files
                calls filename.find_all_files
                calls filename.find_files_in_range'''

        file = obj.name

        if not quiet:
            log.info('Getting list of other files around '+os.path.basename(file))

        #num_minutes=360
        if not quiet:
            log.info('num_minutes merge search time set to:'+str(num_minutes))

        fn = obj.open_new(file)
        startfn = obj.open_new(file)
        startfn.datetime = fn.datetime-timedelta(minutes=num_minutes)
        endfn = obj.open_new(file)
        endfn.datetime = fn.datetime+timedelta(minutes=num_minutes)

        # Was not previously checking different days - loop through all
        # possible days. Again, this will be fixed by database...
        if startfn.datetime.date() != endfn.datetime.date():
            # range(2) creates [0,1], range(1) only [0], so need +2
            day_count = (endfn.datetime - startfn.datetime).days + 2
            check_fns= [startfn]
            for dt in (startfn.datetime+timedelta(n) for n in range(day_count)):
                new_fn = obj.open_new(file)
                # Need to create a method for this somewhere. just setting datetime 
                # doesn't work because datetime gets set from datetime_fields, not vice versa.
                for dtfield,dtfmt in new_fn.datetime_fields.items():
                    setattr(new_fn,dtfield,dt.strftime(dtfmt))
                check_fns += [new_fn]
        else:
            check_fns = [fn]


        #log.info('startfn: '+startfn.name)
        #log.info('endfn: '+endfn.name)

        allfiles = []
        checked_dirs = []
        for curr_fn in check_fns:

            wildfn = obj.set_wildcards(curr_fn.name)

            #print 'wildfn: '+wildfn.name
            #log.info('obj: '+obj.name)

            for base_dir in obj.check_dirs_for_files():
                if os.path.join(base_dir, curr_fn.name) not in checked_dirs:
                    wildfn.base_dir = base_dir
                    if not quiet:
                        log.info('Checking '+wildfn.name+' for '+str(num_minutes)+': '+str(startfn.datetime)+' to '+str(endfn.datetime))
                    allfiles += obj.find_all_files(wildfn,fn,startfn,endfn,extra=extra,quiet=True)
                    checked_dirs += [os.path.join(base_dir,curr_fn.name)]

        if not quiet:
            log.info('    Cleaning up list')
        #print allfiles
        #print file
# tried setting optime to * in the swath files to make sure we caught all 
# the appropriate files to merge, then needed to do glob instead of filecmp 
# when there was a * (literally looked for '*' in filename for filecmp). 
# but fixed that issue by naming the swath images using the actual overpass 
# time, not the start data time, so did not need '*' in filenames anymore.
# Also, glob(file) should always work (which will work for * or no *, so 
# should be able to just use that instead of trying to use filecmp.cmp at all.
# Should probably watch this to make sure nothing funny happens....) MLS
        otherfiles = [xx for xx in allfiles if xx not in glob(file) and '.processing' not in xx]
        # If we do not want duplicate times (RDR conversions), just grab the latest
        # one that matches
        if not duplicates:
            if not quiet:
                log.info('Trimming duplicate times')
            dts = {}
            for currfile in sorted(otherfiles,reverse=True):
                fobj = obj.open_new(currfile)
                if fobj.date+fobj.time not in dts.keys():
                    dts[obj.open_new(currfile).datetime] = currfile
            otherfiles = dts.values()
        #print otherfiles
#        if '*' in file:
#            otherfiles = [xx for xx in allfiles if xx not in glob(file) and '.processing' not in xx]
#        else:
#            otherfiles = [xx for xx in allfiles if not filecmp.cmp(xx,file) and '.processing' not in xx]
        #otherfiles = [xx for xx in allfiles if not (DataFileName(xx).datetime == DataFileName(file).datetime) and '.processing' not in xx]
        if all:
            return [file]+otherfiles
        log.debug('other files before trimming: '+str(otherfiles))
        # We need an odd number of granules to make a complete set for conversion
        if trim and otherfiles and len(otherfiles) % 2 != 0:
            dt0 = obj.open_new(otherfiles[0]).datetime
            dt1 = obj.open_new(otherfiles[-1]).datetime
            # Pop the outlier from the list
            if (fn.datetime - dt0) > (dt1 - fn.datetime):
                otherfiles.pop(0)
            else:
                otherfiles.pop(-1)
        #print otherfiles
        #print trim
        log.debug('other files after trimming: '+str(otherfiles))
        # We need more than one to do the conversion properly.
        # May want to put something in satellite_info to allow 
        # different numbers of granules for different sensors
        #print otherfiles
        if trim:
            if len(otherfiles) > 1:
                return otherfiles
            else:
                return []
        else:
            return otherfiles


#############################################################
### get_other_files, find_files_in_range, and find_all_files should go in filename.py
### pull out list_other_files, check_dirs_for_files, open_new, and set_wildcards in individual subclasses
#############################################################
    def find_all_files(self,wildfn,fn,startfn,endfn,extra=None,quiet=True):
        '''This returns all files that appropriately match fn
            wildfn is the original fn, with appropriate wildcards.
            fn is the actual filename we are trying to match to
            startfn is the earliest file we should match
            endfn is the latest file we should match.
            extra is a string that should be found in the extra field
                of any matched file.
            original call: datafilename.list_other_files
                calls filename.get_other_files
                    calls datafilename.set_wildcards
                    calls datafilename.check_dirs_for_files
                calls filename.find_all_files
                calls filename.find_files_in_range'''
        allfiles = self.find_files_in_range(glob(wildfn.name),
                                            startfn.datetime,
                                            endfn.datetime,
                                            extra=extra,
                                            quiet=True,
                                           )

        if endfn.date != fn.date:
            wildfn.date = endfn.date
            log.debug('Checking '+wildfn.name)
            allfiles.extend(self.find_files_in_range(glob(wildfn.name),
                                            startfn.datetime,
                                            endfn.datetime,
                                            extra=extra,
                                            quiet=True,
                                           ))
        if startfn.date != fn.date:
            wildfn.date = startfn.date
            log.debug('Checking '+wildfn.name)
            allfiles.extend(self.find_files_in_range(glob(wildfn.name),
                                            startfn.datetime,
                                            endfn.datetime,
                                            extra=extra,
                                            quiet=True,
                                           ))
        return allfiles

#############################################################
### get_other_files, find_files_in_range, and find_all_files should go in filename.py
### pull out list_other_files, check_dirs_for_files, open_new, and set_wildcards in individual subclasses
#############################################################
    def find_files_in_range(self,files,start_time,end_time,urlpath=None,extra=None, quiet=False):
        '''find_files_in_range takes a list of files and filters them 
            by only returning those files that fall between start_time
            and end_time.
                files is the list of files we should filter 
                start_time is the earliest datetime we should match
                end_time is the earliest datetime we should match
                if urlpath is passed - we must add it back into
                    the filename
                extra is a string that should be found in the extra field
                    of any matched file.
            called as:
                datafilename.list_other_files
                calls filename.get_other_files
                    calls datafilename.set_wildcards
                    calls datafilename.check_dirs_for_files
                calls filename.find_all_files
                calls filename.find_files_in_range'''
        getfiles = []
        log.debug('Finding files matching requested time...')
        for file in files:  
            dfn = self.open_new(file)
            dt = dfn.datetime
            if extra and hasattr(dfn,'extra') and extra not in dfn.extra:
                #log.info('    Skipping file, Only matching with '+extra+' in extra field')
                pass
            elif dt is None:  
                log.info('    Skipping file, does not match file name format '+file)
            elif (dt <= end_time and dt >= start_time):
                if urlpath != None:
                    file = urlpath+'/'+file
                log.debug('    file matches: '+file+' '+str(dt)+' '+str(start_time)+' '+str(end_time))
                if not quiet:
                    log.info('    file matches: '+os.path.basename(file))
                getfiles.append(file)

        getfiles.reverse()

        if getfiles == []:
            log.info('No files found between '+str(start_time)+' and '+str(end_time))

        return getfiles

def parse(name, nameformat, fieldsep='.', fillvalue='_',ext=None):
    '''Parses input file name.
    For each field, adds a property to the FileName class.
    '''
    #print 'starting parse, for everything! ext: '+str(ext)+' name: '+str(name)+' format: '+str(nameformat)
    #Get the name of each field by spligging the format string at the fieldseps
    formatparts = []
    nameparts = []
    # Is this supposed to work for dirnames and basenames ? If so, need to split on '/'
    # first, then split on fieldsep.  If it is a basename (with no '/'s), then this will
    # just happen once, and it is the same as before. Should explicitly pass os.path.basename
    # or dirname, and not do it here.

    # Do these backwards, so if we are doing paths, the beginning of the
    # path can be reserved for a base directory (the extra '/'s throw it off)
    nameformat_paths = nameformat.split(os.path.sep)
    name_paths = name.split(os.path.sep)
    name_paths.reverse()
    nameformat_paths.reverse()

    #print '    parse nameformat: '+str(nameformat_paths)+' name: '+str(name_paths)
    if len(name_paths) > len(nameformat_paths):
        #I'm sure there's a better way to do this...
        # take everything from len(format) on and combine into 
        startind = len(nameformat_paths) - 1
        #print '    parse name_paths[startind:]: '+str(name_paths[startind:])
        #print '    parse name_paths[startind+1:]: '+str(name_paths[startind+1:])
        try:
            name_paths[startind] = os.path.sep.join(
                    list(reversed(name_paths[startind+1:])) + 
                    [name_paths[startind]]
                    )
        except:
            log.warning('failed')
            #raise
        name_paths = name_paths[0:startind+1]
        #print '    parse name_paths now: '+str(name_paths)
        #print '    parse len(name_parts): '+str(len(name_paths))+' len(name_paths): '+str(len(nameformat_paths))

    
    all_paths = zip(nameformat_paths,name_paths)
    for (nameformat_path,name_path) in all_paths:
        formatparts += nameformat_path.split(fieldsep)
        #print '        parse formatparts: '+str(formatparts)
        #print '        length: '+str(len(formatparts))
        #Get the value of each field by splitting the basename at the fieldseps
        #nameparts = os.path.basename(name).split(fieldsep)
        # Is this supposed to work for directories and filenames.... ? If so, we should be
        # passing either the filename or the dirname, so don't do os.path.basename here...
        # If the nameformat_path does not have a fieldsep in it, do not
        # split the actual path on fieldsep - this was making True-Color
        # fail because fieldsep was '-'
        if fieldsep in nameformat_path:
            #print 'fieldsep in '+nameformat_path
            nameparts += name_path.split(fieldsep)
        else:
            #print 'no fieldsep in '+nameformat_path
            nameparts += [name_path]
        #print '        parse nameparts: '+str(nameparts)
        #print '        length: '+str(len(nameparts))
    #Test format
    if len(nameparts) != len(formatparts):
        #shell()
        raise PathFormatError('Filename %s does not conform to format string: %s' % 
                          (name, nameformat))
    #Create a dictionary with field names as keys and field values as values
    fields = dict(zip(formatparts, nameparts))
    if ext:
        fields['<ext>'] = ext                         #Dictionary of file name fields
    #print 'leaving parse fields: '+str(fields)
    return fields


def make_new_name(nameformat, fieldsep, parts,dt=None,ext=None,fillvalue=None,pathfillvalue=None):
    '''Replace each field with its respective field from self.fields
    REGEX NOTES:
       First MAIN group:
           Looks for either of the following sub groups but does not include them
               in the match
           First SUB group:
               looks before the main match for a start of line character
           Second SUB group:
               looks before the main match for a period (.)
       Main match string:
           The name of the format part (e.g. date) to be replaced
       Second MAIN group:
           Looks for either of the following sub groups but does not include them
               in the match
           First SUB group:
               looks after the main match for a period (.)
           Second SUB group:
               looks after the main match for an end of line character
    '''
    #print 'starting make_new_name fieldsep: '+str(fieldsep)+' nameformat: '+str(nameformat)+' parts: '+str(parts)
    if not nameformat:
        return ''
    tempname = copy(nameformat)
    #print '    make_new_name parts: '+str(parts)
    #shell()
    isdir = False
    if os.path.sep in nameformat:
        isdir = True
    for dirname in reversed(nameformat.split(os.path.sep)):
        for format_part in reversed(dirname.split(fieldsep)):
            dtstring = None
            #print '    make_new_name format_part: '+str(format_part)
            format_part_name = format_part
            if '<' in format_part:
                format_part_name = format_part_name.replace('<','').replace('>','')
                #print '    make_new_name<: '+format_part_name
            else:
                # force variable path elements to be surrounded by <> (so we can have 
                # static portions of the path as well)
                #print '    make_new_name: no <>, so static field'
                continue
            if '{' in format_part:
                try:
                    format_part_name,dtformatstring = format_part_name.split('{',2)
                except:
                    log.warning('failed')
                dtformatstring = dtformatstring.replace('}','')
                #print '    make_new_name{: '+format_part_name
                #print '    make_new_name parts[format_part_name]:'+parts[format_part_name]
                #print '    make_new_name pathfillvalue:'+str(pathfillvalue)
                #print '    make_new_name fillvalue:'+str(fillvalue)
                if parts[format_part_name] == pathfillvalue:
                    dtstring = pathfillvalue
                elif parts[format_part_name] == fillvalue:
                    dtstring = fillvalue
                # Allow wildcards in date/time fields
                elif dt and '*' not in parts[format_part_name]: 
                    #print '    make_new_name parts[format_part_name]:'+parts[format_part_name]+' format_part_name: '+format_part_name
                    dtstring = dt.strftime(dtformatstring)


            escaped_format_part = re.escape(format_part)
            escaped_fieldsep = re.escape(fieldsep)
            escaped_ospathsep = re.escape(os.path.sep)

            regex_pattern =  (
                r'((?<=/)|(?<=^)|(?<=%s)|(?<=%s))%s((?=%s)|(?=$)|(?=/)|(?=%s))' % 
                (escaped_fieldsep, escaped_ospathsep, 
                 escaped_format_part, 
                 escaped_fieldsep, escaped_ospathsep))
            try:
                if dtstring:
                    repl_string = dtstring
                # If the format string has <ext>, use the passed value of the extension
                elif format_part_name == "ext" :
                    if ext:
                        repl_string = r'%s' % ext
                    # If ext is None, replace with 'ext'
                    else:
                        repl_string = "ext"
                else:
                    #print '    make_new_name format_part_name: '+str(format_part_name)
                    repl_string = r'%s' % parts[format_part_name]
            except KeyError:
                if isdir and pathfillvalue:
                    repl_string = r'%s' % pathfillvalue
                else:
                    raise PathFormatError('Filename does not conform to format string: %s' % nameformat)
            # replace current format name with actual name in format string.
            #print '    make_new_name regex_pattern: '+regex_pattern+' repl_string: '+repl_string
            if '\\' in repl_string:
                repl_string = repl_string.replace('\\','\\\\')                
            try:
                tempname = re.sub(regex_pattern, repl_string, tempname)
            except:
                log.warning('failed')
                raise
            #print '    tempname: '+tempname
        #print 'leaving make_new_name tempname: '+str(tempname)
    return tempname
