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

# 20150630  Mindy  Add AHIDATFileName/AHIHPCtgzFileName for Himawari
#                   Add AMSUFileName/AMSUTDFFileName (AMSUTDFFileName comes
#                       directly from converter, AMSUFileName comes from 
#                       nesdis)
#                   Add ASCATFileName
#                   Add AMSR2FileName
#                   Add FNMOCBFTGSFileName for mtsat/msg (includes geo_simple 
#                       information). JAMITDF/SEVIRITDF for converted data
#                   Add GPMFileName
#                   Change JAMI to JAMITDF (also uses FNMOCBFTGSFileName)
# 20150701  Mindy  Added scifile_source to all DataFileName object set_fields 
#                   methods

# Python Standard Libraries
import os
import logging
import sys
from datetime import datetime,timedelta
import traceback
from glob import glob
import pdb


# Installed Libraries
from IPython import embed as shell


# GeoIPS Libraries
from ..plugin_paths import paths
from ..log_setup import interactive_log_setup
from ..satellite_info import all_available_sensors,all_sats_for_sensor,SatSensorInfo
from .filename import FileName
from .exceptions import PathFormatError


log = interactive_log_setup(logging.getLogger(__name__))


# Standard Name Format for Auxiliary files - formats for data files are defined in satellite_info.py
aux_unsectored_name = 'UNSECTORED'
stdauxnameformat = '<date{%Y%m%d}>.<time{%H%M%S}>.<satname>.<sensorname>.<extdatatype>.<sectorname>.<dataprovider>.<extra>'
stdauxfieldsep = '.'
stdauxfillvalue='x'
stdauxnoext = False
# longterm_or_intermediate = longterm_files or intermediate_files
# extdatacategory geoalgs
# extdatatype elevation
stdauxpathnameformat=paths['SATOPS']+'/<longterm_or_intermediate>/<extdatacategory>/<extdatatype>'
stdauxpathfieldsep = '-'
stdauxpathfillvalue = 'x'



class DataFileName(object):
    '''
    provide an interface to easily create and 
    modify data specific filenames.
    While FileName requires `path` and `nameformat`, DataFileName can be called
    with no arguments, creating a `fillvalue` filled 'empty' filename in the default
    `nameformat`. the _propertyTest tests are NOT performed when field value is `fillvalue` 

        >>> df = DataFileName()
        >>> df.name = 'x.x.x.x.x.x.x.x.x.ext'

    If DataFileName() is called with one of 
        nameformat
        fieldsep
        fillvalue
        pathnameformat      
        pathfieldsep
        pathfillvalue
    it must be called with ALL. This will override trying to use the default 
    file name formats found in utils/satellite_info.py

    '''
    def __new__(typ, path=None,
            nameformat=None,
            fieldsep=None,
            fillvalue=None,
            pathnameformat=None,
            pathfieldsep=None,
            pathfillvalue=None,
            noextension=False,
            auxdata=False):
        # The standard filename format is included in the SatSensorInfo class in
        # utils/satellite_info.py
        si = SatSensorInfo()
        #print '__new__ in DataFileName'

        # If neither path nor nameformat included, use defaults from SatSensorInfo,
        # and create empty path
        if not path and not nameformat:
            #print 'Neither path nor nameformat passed'
            if auxdata:
                stdfn = (stdauxfieldsep.join([stdauxfillvalue for field in (stdauxnameformat.split(stdauxfieldsep))]))+'.ext'
                #print stdfn
                stdpathparts = []
                for pathpart in stdauxpathnameformat.split('/'):
                    pathpart = pathpart.strip()
                    if not pathpart:
                        stdpathpart = ''
                    else:
                        #print '    pathpart: '+str(pathpart)
                        stdpathpart = (stdauxpathfieldsep.join([stdauxpathfillvalue for field in (pathpart.split(stdauxpathfieldsep))]))
                        #print '    stdpathpart: '+str(pathpart)
                    stdpathparts += [stdpathpart]
                stdpath = '/'.join(stdpathparts)
                #print stdpath
                #print 'full empty stdpath from ProductFileName(): '+stdpath+'/'+stdfn
                obj = StandardAuxDataFileName(stdpath+'/'+stdfn,
                        nameformat=stdauxnameformat,
                        fieldsep=stdauxfieldsep,
                        fillvalue=stdauxfillvalue,
                        pathnameformat=stdauxpathnameformat,
                        pathfieldsep=stdauxpathfieldsep,
                        pathfillvalue=stdauxpathfillvalue,
                        noextension=stdauxnoext )
            else:
                path = typ.create_empty_basename(si.FName['fieldsep'],si.FName['fillvalue'],si.FName['nameformat'],'.ext')
                obj = StandardDataFileName(path,
                            nameformat=si.FName['nameformat'],
                            fieldsep=si.FName['fieldsep'],
                            fillvalue=si.FName['fillvalue'],
                            pathnameformat=si.FName['pathnameformat'],
                            pathfieldsep=si.FName['pathfieldsep'],
                            pathfillvalue=si.FName['pathfillvalue'],
                            noextension=si.FName['noextension'])
                obj.sensorinfo = si
            return obj

        # If nameformat is included (and all associated parameters!), but path is not,
        # use passed formats to create empty path, and create empty StandardDataFileName 
        # object of the format that was passed.
        if not path and nameformat:
            if auxdata:
                path = typ.create_empty_basename(fieldsep,fillvalue,nameformat,'.ext')
                obj = StandardAuxDataFileName(path,nameformat,fieldsep,fillvalue,
                        pathnameformat,pathfieldsep,pathfillvalue,noextension)
                # This needs to be handled differently... Right now dynamic properties in the path that are not in filename  
                # need to be added explicitly here
                # This probably should be handled in filename.py ? 
                obj._add_property('extdatacategory')
                obj._add_property('longterm_or_intermediate')
                obj.sensorinfo = None
            else:
                path = typ.create_empty_basename(fieldsep,fillvalue,nameformat,'.ext')
                obj = StandardDataFileName(path,nameformat,fieldsep,fillvalue,
                        pathnameformat,pathfieldsep,pathfillvalue,noextension)
                obj.sensorinfo = None
            return obj

        # If path and nameformat are included, use passed format and passed path
        # to create StandardDataFileName object
        if path and nameformat:
            #print 'path and nameformat passed to StandardDataFileName: '+str(path)+' '+str(nameformat)
            if auxdata:
                obj = StandardAuxDataFileName(path,nameformat,fieldsep,fillvalue,
                    pathnameformat,pathfieldsep,pathfillvalue,noextension
                    )
            else:
                obj = StandardDataFileName(path,nameformat,fieldsep,fillvalue,
                    pathnameformat,pathfieldsep,pathfillvalue,noextension
                    )
                obj.sensorinfo = None
            return obj

        # If path and not name format - try default StandardDataFileName first
        try:
            #print 'path and not name format: '+str(si.FName)
            # This will return StandardDataFileName object if the path is in the 
            # default format found in SatSensorInfo.
            obj = StandardDataFileName(path,
                nameformat=si.FName['nameformat'],
                fieldsep=si.FName['fieldsep'],
                fillvalue=si.FName['fillvalue'],
                pathnameformat=si.FName['pathnameformat'],
                pathfieldsep=si.FName['pathfieldsep'],
                pathfillvalue=si.FName['pathfillvalue'],
                noextension=si.FName['noextension'])
            #print 'Trying StandardDataFileName sat/sensor: '+obj.satname+' '+obj.sensorname+' for '+obj.name
            si = SatSensorInfo(obj.satname,obj.sensorname)
            #print si
            #print sys.modules[__name__]
            #print si.FName
            #print si.FName['cls']
            #print getattr(sys.modules[__name__],si.FName['cls'])
            # The returned object will be of type StandardDataFileName, we need
            # it to be of type <satname><sensorname>Info, so open again.
            obj = getattr(sys.modules[__name__],si.FName['cls'])(path,
                nameformat=si.FName['nameformat'],
                fieldsep=si.FName['fieldsep'],
                fillvalue=si.FName['fillvalue'],
                pathnameformat=si.FName['pathnameformat'],
                pathfieldsep=si.FName['pathfieldsep'],
                pathfillvalue=si.FName['pathfillvalue'],
                noextension=si.FName['noextension'])
            obj.sensorinfo = si
            # MLS ?????????? Not sure how to handle this, probably shouldn't
            # be directly adding the dynamic property...
            obj._add_property('base_dir')
            setattr(obj,'base_dir',obj.sensorinfo.FName['base_dirs'][0])
            for base_dir in obj.sensorinfo.FName['base_dirs']:
                if base_dir and base_dir in path:
                    setattr(obj,'base_dir',base_dir)
                    break
            #print 'Using StandardDataFileName '+obj.satname+' / '+obj.sensorname+' for '+obj.name
            obj = obj.standard_set_fields(obj)
            return obj
        except PathFormatError:
            # If it is not in our default StandardDataFileName format, move on.
            #print traceback.format_exc()
            pass

        try:
            obj = StandardAuxDataFileName(path,
                nameformat=stdauxnameformat,
                fieldsep=stdauxfieldsep,
                fillvalue=stdauxfillvalue,
                pathnameformat=stdauxpathnameformat,
                pathfieldsep=stdauxpathfieldsep,
                pathfillvalue=stdauxpathfillvalue,
                noextension=stdauxnoext)
            #print 'StandardAuxDataFileName from path'
            # This needs to be handled differently... Right now dynamic properties in the path need to be added explicitly here
            # This probably should be handled in filename.py ? 
            obj._add_property('extdatacategory')
            obj._add_property('longterm_or_intermediate')
            obj = obj.standard_set_fields(obj)
            return obj
        except PathFormatError:
            pass

        # Now if path and not name format, and it was not in our StandardDataFileName
        # default format, try every SatSensorInfo combination until we find one that 
        # matches
        for sensor in all_available_sensors():
            for sat in all_sats_for_sensor(sensor):
                #print 'trying '+sat+' '+sensor
                obj = typ.from_satsensor(sat,sensor,path)
                if obj:
                    return obj
                else:
                    continue

        # Too bad if we make it here.  Nothing matched.

    @staticmethod 
    def list_range_of_files(platformname,sourcename,start_datetime,end_datetime,
            datetime_wildcards={'%H':'*','%M':'*','%S':'*'},
            data_provider=None,
            resolution=None,
            channel=None,
            producttype=None,
            area=None,
            extra=None,
            ext='*',
            forprocess=False):
        '''List all matching files with certain parameters (used for process_overpass,
            latency, etc).  Eventually this will be replaced with a simple
            database call.  Currently uses wildcards to find appropriate files.
            forprocess=True returns directories if runfulldir is set'''
        dfn = DataFileName.from_satsensor(platformname,sourcename,wildcards=True)
        if not producttype:
            producttype = '*'
        if not resolution:
            resolution = '*'
        if not data_provider:
            data_provider = '*'
        if not channel:
            channel = '*'
        if not area:
            area = '*'
        if not extra:
            extra = '*'
        files = []
        for currdfn in [dfn]:
            from geoips.utils.path.filename import daterange
            print_dtstrs = "      "
            for curr_dt in daterange(start_datetime,end_datetime,hours=True):
                dfn = DataFileName.from_satsensor(platformname,sourcename,path=currdfn.name)
                dfn.datetime = curr_dt
                #shell()
                dt_strs = dfn.set_datetime_str(datetime_wildcards=datetime_wildcards,datetime_fields=dfn.datetime_fields) 
                for dt_field in dfn.datetime_fields.keys():
                    dfn.datetime = curr_dt
                    setattr(dfn,dt_field,dt_strs[dt_field])
                    print_dtstrs += ' '+str(dt_strs[dt_field])
                dfn.datetime = curr_dt
                dfn.satname = platformname
                dfn.sensorname = sourcename
                dfn.resolution = resolution
                dfn.channel = channel
                dfn.producttype = producttype
                dfn.area = area
                dfn.extra = extra
                dfn.ext = ext
                # This is lame. Things get screwy with resetting wildcarded datetime fields...
                # dfn.date appears to have to be last (maybe recalcluates path with each
                # update?
                #  will go away with database...
                if forprocess and dfn.sensorinfo.FName['runfulldir']:
                    files += glob(os.path.dirname(dfn.name))
                else:
                    files += glob(dfn.name)
            log.info('Trying '+dfn.name)
            log.info(print_dtstrs)

        return list(set(files))


    @staticmethod
    def create_empty_basename(fieldsep,fillvalue,nameformat,ext='',directory=False):
        '''Create a path with 'fillvalue' in every field, separated by 'fieldsep'''
        if nameformat:
            if directory:
                retval = ''
                for dirlevel in nameformat.split('/'):
                    if retval:
                        retval += '/'
                    retval += (fieldsep).join([fillvalue for field in (dirlevel).split(fieldsep)])
                    #print retval
                return retval
            return (fieldsep).join([fillvalue for field in (nameformat).split(fieldsep)])+ext
        else:
            return ''


    @staticmethod
    def from_satsensor(sat,sensor,path=None,wildcards=False):
        '''Return appropriate DataFileName subclass object using passed sat/sensor'''

        #testsensor = 'model'; testsat = 'model'
        # Open appropriate SatSensorInfo object
        #print sat
        si = SatSensorInfo(sat,sensor)

        retobj = None
        for origfname in si.OrigFNames+[si.FName]:
            #if sat == 'model' and sensor == 'model': print 'origfname '+str(origfname)
            try:
                #if 'model' == sat and sensor == 'model': print 'origfname '+str(origfname)
                # Wildcards as fillvalue is useful for finding lists of all files
                # meeting certain criteria.
                if wildcards:
                    fnfillvalue = '*'
                    pathfillvalue = '*'
                    ext = '.*'
                # Otherwise use the fillvalues from SatSensorInfo object
                else:
                    fnfillvalue = origfname['fillvalue']
                    pathfillvalue = origfname['pathfillvalue']
                    ext = '.'+origfname['fillvalue']
                if origfname['noextension'] == True:
                    ext = ''

                currpath = path
                #if sat == 'model' and sensor == 'model': print 'passed path: '+str(path)


                # If we did not pass a path, create an empty filename from the
                # appropriate DataFileName formats
                if not path:
                    currpath = DataFileName.create_empty_basename(origfname['fieldsep'],
                         fnfillvalue,origfname['nameformat'],ext=ext)
                    currdir = DataFileName.create_empty_basename(origfname['pathfieldsep'],
                         pathfillvalue,origfname['pathnameformat'],ext='',directory=True)
                    currpath = currdir+'/'+currpath
                    #print 'empty path: '+str(currpath)
                #if sat == testsat and sensor == testsensor: print 'pathnameformat: '+str(origfname['pathnameformat'])
                #if sat == testsat and sensor == testsensor: print 'pathnameformat: '+str(origfname['nameformat'])
                #if sat == testsat and sensor == testsensor: print 'noextension: '+str(origfname['noextension'])
                #if sat == testsat and sensor == testsensor: print getattr(sys.modules[__name__],origfname['cls'])
                #if sat == testsat and sensor == testsensor: print currpath
                #if testsensor == sensor: from IPython import embed as shell; shell()
                # Try to open the DataFileName subclass specified in origfname['cls'],
                # using the specified path and format. Will raise an error if it does
                # not match (which is caught below, and None is returned. Maybe should
                # just raise and catch in __new__ above...)
                # Note: If this is failing, try uncommenting the traceback in the except below.
                #       then you can at least see the error.
                obj = getattr(sys.modules[__name__],origfname['cls'])(currpath,
                    nameformat=origfname['nameformat'],
                    fieldsep=origfname['fieldsep'],
                    fillvalue=fnfillvalue,
                    pathnameformat=origfname['pathnameformat'],
                    pathfieldsep=origfname['pathfieldsep'],
                    pathfillvalue=pathfillvalue,
                    noextension=origfname['noextension'])
                # Check if we have a different satname in orig filename
                if hasattr(obj,'satname') and obj.satname != obj.get_fillvalue() and si.orig_file_satname and si.orig_file_satname != obj.satname:
                    continue
                si.OrigFName = origfname
                # print 'Using '+sat+' / '+sensor
                # print obj
                # print 'noextension: '+str(origfname['noextension'])
                obj.sensorinfo = si
                if obj:
                    # MLS Not sure how to handle this, probably shouldn't
                    # be directly adding the dynamic property...
                    obj._add_property('base_dir')
                    for base_dir in si.FName['base_dirs']:
                        # Default to first base_dir in base_dirs list ?
                        setattr(obj,'base_dir',base_dir)
                        # Overwriting with correct one as we loop through ?
                        if base_dir and path and base_dir in path and base_dir not in obj.base_dir:
                            setattr(obj,'base_dir',base_dir)
                # Must check that object meets the istype() criteria (if multiple 
                # filename formats match, must use something within a field to 
                # tell if it is of the desired type. ie, VIIRS vs ATMS files)
                # If we did not pass a path, the object will not meet the istype()
                # criteria (since all the fields are fillvalue), so still return object
                if not path or obj.istype():
                    retobj = obj
                # Otherwise we did not match, return None 
            # This will fail if everything is not defined in satellite_info
            # for a specific satellite/sensor, or if the format doesn't match. 
            # Skip the undefined ones for now, add info
            # in satellite_info to get them to work.
            except (PathFormatError,KeyError,ValueError,IndexError),resp:
                #if testsensor == sensor: print traceback.format_exc()
                #print traceback.format_exc()
                continue


        ####Don't think OrigFName always works - can't across the board reset fields (since they
        ####    are not standard for OrigFNames

        return retobj

    @staticmethod
    def _dateTest(date):
        '''
        _dateTest is NOT performed when field value is `fillvalue` 
        See dynamicprops._part_setter
        Otherwise, raise PathFormatError if invalid field
        '''
        if len(date) != 8 or not date.isdigit():
            raise PathFormatError('Date field must be of the form YYYYMMDD.  Got %s' % date)

    @staticmethod
    def _timeTest(time):
        '''
        _timeTest is NOT performed when field value is `fillvalue` 
        See dynamicprops._part_setter
        Otherwise, raise PathFormatError if invalid field
        '''
        if len(time) != 6 or not time.isdigit():
            raise PathFormatError('Time field must be of the form HHMMSS.  Got %s' % time)



class StandardAuxDataFileName(FileName):
    '''
    Standard External Data filenames, this can be subclassed to provide descriptions
    of non-standard external data filenames. IF IT GETS SUBCLASSED, NEED TO ADD NEW
    SUBCLASSES TO DataFileName !!!
    '''

    def open_new(self,fnamestr=None):
        if fnamestr:
            return DataFileName(fnamestr)
        else:
            return DataFileName()

    @staticmethod
    def frominfo(isunsectored = False,
                    sectorname=None,
                    extdatatype = None,
                    dataprovider=None,
                    extra=None,
                    ext='dat',
                    ):
        xf = DataFileName(auxdata=True)

        xf = xf.standard_set_fields(xf,isunsectored=isunsectored,sectorname=sectorname,extdatatype=extdatatype,dataprovider=dataprovider,extra=extra,ext=ext)

        dt = datetime.utcnow()
        xf.time = dt.strftime(xf.datetime_fields['time'])
        xf.date = dt.strftime(xf.datetime_fields['date'])

        return xf

    @staticmethod
    #isunsectored overrides setting of sectorname in call - always set to unsectored_name 
    def find_existing_file(isunsectored = False,
                    sectorname=None,
                    extdatatype = None,
                    dataprovider=None,
                    extra=None,
                    ext='dat',
                    retobj=False
                    ):
        xf = DataFileName(auxdata=True)

        xf = xf.standard_set_fields(xf,isunsectored=isunsectored,sectorname=sectorname,extdatatype=extdatatype,dataprovider=dataprovider,extra=extra,ext=ext)

        xf.date = '*'
        xf.time = '*'

        xfnames = glob(xf.name)
        if xfnames:
            if retobj:
                return DataFileName(xfnames[0])
            else:
                return xfnames[0]
        # Try UNSECTORED external data file, if sectored does not yet exist
        else:
            xf.sectorname = aux_unsectored_name
            xfnames = glob(xf.name)
            if xfnames:
                if retobj:
                    return DataFileName(xfnames[0])
                else:
                    return xfnames[0]

        return None

    def create_standard(self,geoips=True):
        xf = DataFileName(path=None,
                nameformat=stdauxnameformat,
                fieldsep=stdauxfieldsep,
                fillvalue=stdauxfillvalue,
                pathnameformat=stdauxpathnameformat,
                pathfieldsep=stdauxpathfieldsep,
                pathfillvalue=stdauxpathfillvalue,
                auxdata=True)
        #print 'StandardAuxDataFileName create_standard '+str(xf)
        xf = self.standard_set_fields(xf)
        return xf

    def needs_updated(self):

        unsectored_file = self.create_standard()
        unsectored_file.date = '*'
        unsectored_file.time = '*'
        unsectored_file.ext = '*'
        unsectored_file.sectorname = aux_unsectored_name
        # if glob doesn't return anything for wildcarded unsectored_file name,
        # that means it doesn't exist.  Which shouldn't be the case ?! So raise
        # IOError
        try:
            unsectored_fnstr = glob(unsectored_file.name)[0]
        except IndexError:
            raise IOError('Original unsectored external data file does not exist: '+unsectored_file.name)

        unsectored_file = DataFileName(unsectored_fnstr)
        
        existing_file = self.create_standard()
        existing_file.date = '*'
        existing_file.time = '*'
        # If there are no existing files, then we need to create it, return true
        try:
            existing_fnstr = glob(existing_file.name)[0]
        except IndexError:
            return True

        existing_file = DataFileName(existing_fnstr)
        if not os.path.exists(unsectored_fnstr):
            return True
        if existing_file.datetime > unsectored_file.datetime:
            return False
        return True

    def delete_old_files(self):
        '''delete_old_files removes duplicate files.
            delete_old_files in productfilename calls list_other_files,
                datafilename.delete_old_files is stand alone.
                Perhaps that should change ?'''

        log.info('Removing old files around '+self.name)

        existing_file = self.create_standard()
        existing_file.date = '*'
        existing_file.time = '*'
        existing_fnstrs = glob(existing_file.name)
        deleted_fnstrs = []
        try:
            newest_fnstr = existing_fnstrs.pop()
        except IndexError:
            return deleted_fnstrs

        for existing_fnstr in existing_fnstrs:
            newest_file = DataFileName(newest_fnstr)
            existing_file = DataFileName(existing_fnstr)
            if existing_file.datetime > newest_file.datetime:
                newest_fnstr = existing_fnstr
                newest_file.unlink()
                deleted_fnstrs.append(newest_file.name)
            elif newest_file.datetime > existing_file.datetime:
                existing_file.unlink()
                deleted_fnstrs.append(existing_file.name)
        return deleted_fnstrs



    def standard_set_fields(self,xf,isunsectored=False,sectorname=None,extdatatype=None,dataprovider=None,extra=None,ext=None,scifile_obj=None):
        xf = self.set_fields(xf, isunsectored, sectorname, extdatatype, dataprovider, extra, ext, scifile_obj)
        if hasattr(xf, 'extra'):
            xf.extra = xf.extra.replace('.', 'p')
        return xf

    def set_fields(self,xf,isunsectored=False,sectorname=None,extdatatype=None,dataprovider=None,extra=None,ext=None,scifile_obj=None):

        #print 'set_fields'

        xf.date = self.date
        xf.time = self.time
        xf.satname = self.satname
        xf.sensorname = self.sensorname
        xf.extdatatype = self.extdatatype

        # set in create_standard()
        xf.dataprovider = self.dataprovider 
        xf.sectorname = self.sectorname
        xf.extra = self.extra
        xf.ext = self.ext
        xf.scifile_source = self.extdatatype

        if isunsectored:
            xf.sectorname = aux_unsectored_name
        elif sectorname:
            xf.sectorname = sectorname


        #print 'xf datatype: '+str(xf.extdatatype)
        #print 'passed datatype: '+str(extdatatype)
        if extdatatype:
            xf.extdatatype = extdatatype
        if dataprovider:
            xf.dataprovider = dataprovider
        if extra:
            xf.extra = extra

        if xf.extdatatype in ['elevation','emissivity']:
            xf.longterm_or_intermediate = 'longterm_files'
            xf.extdatacategory = 'geoalgs_data'
        elif xf.extdatatype in ['basemap']:
            xf.longterm_or_intermediate = 'longterm_files'
            xf.extdatacategory = 'pickles'
        else:
            xf.longterm_or_intermediate = 'intermediate_files'
            xf.extdatacategory = 'x'


        if ext:
            xf.ext = ext

        return xf



class StandardDataFileName(FileName):

#############################################################
### get_other_files, find_files_in_range, and find_all_files should go in filename.py
### pull out list_other_files, check_dirs_for_files, open_new, and set_wildcards in individual subclasses
#############################################################
    def open_new(self,fnamestr=None):
        if fnamestr:
            return DataFileName(fnamestr)
        else:
            return DataFileName()

#############################################################
### get_other_files, find_files_in_range, and find_all_files should go in filename.py
### pull out list_other_files, check_dirs_for_files, open_new, and set_wildcards in individual subclasses
#############################################################
    def set_wildcards(self,file):
        '''set_wildcards sets wildcards appropriately for the Given
            filename type. For data filenames, we want any extra 
            and any time that matches.
                called as:
                    TYPEfilename.list_other_files
                    calls filename.get_other_files
                        calls TYPEfilename.set_wildcards
                        calls TYPEfilename.check_dirs_for_files
                    calls filename.find_all_files
                    calls filename.find_files_in_range'''
        wildfn = self.open_new(file)
        wildfn.time = '*'
        # BUG!!! time MUST be set before extra !!!!!!
        # for some reason the '*' for time in the path does not take until we set another 
        # field after it. (can be any field, does not have to be something in path, can even be date, 
        # if you set time, then date, after setting time only time in filename is *, but after setting date 
        # date in path and filename and time in path and filename are all *)
        wildfn.extra = '*'
        return wildfn

#############################################################
### get_other_files, find_files_in_range, and find_all_files should go in filename.py
### pull out list_other_files, check_dirs_for_files, open_new, and set_wildcards in individual subclasses
#############################################################
    def check_dirs_for_files(self):
        '''This specifies the directories that should be searched when
            trying to find matching files
            called as:
                TYPEfilename.list_other_files
                calls filename.get_other_files
                    calls TYPEfilename.set_wildcards
                    calls TYPEfilename.check_dirs_for_files
                calls filename.find_all_files
                calls filename.find_files_in_range'''
        return self.sensorinfo.FName['base_dirs']

#############################################################
### get_other_files, find_files_in_range, and find_all_files should go in filename.py
### pull out list_other_files, check_dirs_for_files, open_new, and set_wildcards in individual subclasses
#############################################################
    def list_other_files(self,all=False,trim=False,num_minutes=2,quiet=False, duplicates=True):
        '''list_other_files lists other files matching the current file
            EVENTUALLY THIS WILL BE REPLACED WITH DATABASE CALL
            for datafilename objects, we want to use SatSensorInfo
                to find the appropriate matching information.
            trim=True trims to an odd number of granules
                (need for viirs rdr converter)
            all=True returns all files including original,
            all=False does not include the original filename
            duplicates=True includes files with the same time
            duplicates=False only includes the latest file when more than one with the same time
                called as:
                    TYPEfilename.list_other_files
                    calls filename.get_other_files
                        calls TYPEfilename.set_wildcards
                        calls TYPEfilename.check_dirs_for_files
                    calls filename.find_all_files
                    calls filename.find_files_in_range'''
        si = SatSensorInfo(self.satname,self.sensorname)
        cls = getattr(sys.modules[__name__],si.OrigFName['cls'])
        if hasattr(cls,'get_other_files'):
            return cls.get_other_files(self,all=all,trim=trim,num_minutes=num_minutes,quiet=quiet,duplicates=duplicates)
        else:
            return []

    def all_files_exist(self,channels=None,dir=None):
        ''' Take dirname of current filename object, and check
        for all required channels (as listed in sensorinfo object
        if not passed) in that directory'''


        existing_channels = []
        if not channels:
            if self.sensorinfo and hasattr(self.sensorinfo,'all_prefixes'):
                channels = self.sensorinfo.all_prefixes
            else:
                return True

        if not dir:
            dir = self.dirname().name


        #print set(channels)

        files = glob(dir+'/*')

        for file in files:
            dfn = DataFileName(os.path.basename(file))
            sdfn = dfn.create_standard()
            existing_channels += [sdfn.channel]

        #print set(existing_channels)

        #shell()

        if set(channels) <= set(existing_channels):
            return True
        else:
            return False




    def create_standard(self,downloadSiteObj=None,wildcards=False,scifile_obj=None):
        '''create_standard sets the appropriate fields and returns a
        StandardDataFileName object in the appropriate format. This
        loses the Sat/Sensor FileName subclass (depend on satname/sensorname
        fields to tell what sat/sensor it is)'''

        #print 'StandardDataFileName create_standard'
        if scifile_obj:
            si = SatSensorInfo(scifile_obj.platform_name,scifile_obj.source_name)
        elif self.sensorinfo:
            si = self.sensorinfo
        else:
            si = SatSensorInfo()
        #print '    si: '+str(si)

        if wildcards:
            # If wildcards is True, replace fillvalue with *
            fnfillvalue = '*'
            pathfillvalue = '*'
        else:
            # Otherwise use default fillvalues for satsensor info
            fnfillvalue = si.FName['fillvalue']
            pathfillvalue = si.FName['pathfillvalue']

        #print si.FName
        # Open a new DataFileName object using appropriate values
        df = DataFileName(path=None,
                nameformat=si.FName['nameformat'],
                fieldsep=si.FName['fieldsep'],
                fillvalue=fnfillvalue,
                pathnameformat=si.FName['pathnameformat'],
                pathfieldsep=si.FName['pathfieldsep'],
                pathfillvalue=pathfillvalue)


        #shell()
        # If this is already a StandardDataFileName object, just return
        if not scifile_obj and self.__class__ == df.__class__:
            #print 'Already StandardDataFileName object, return self'
            #print self 
            #print si
            #print 'dp and prodtype: '+self.dataprovider+' '+self.producttype
            #print 'Adding pid and timestamp'
            self._add_property('pid')
            self._add_property('timestamp')
            return self


        # Set this here rather than in set_fields so we don't have to have this
        # same code in set_fields for every subclass. MLS maybe pull this out into
        # a method though and call from all set_fields, for clarity ?
        dataprovider = None
        if hasattr(self,'dataprovider') and self.dataprovider is not self.get_fillvalue():
            #print 'hasattr dataprovider '+self.dataprovider
            dataprovider = self.dataprovider
        elif downloadSiteObj:
            # Pass downloadSiteObj to set dataprovider based on which downloader 
            # we're using (can't always get that information from the filename
            # itself)
            try:
                dataprovider = downloadSiteObj.data_type+'_'+downloadSiteObj.host_type
            except AttributeError:
                log.warning('Must pass download Site Object to set dataprovider. Using default')
        elif scifile_obj:
            dataprovider = 'scifile'
        elif hasattr(self,'dataprovider'):
            #print 'hasattr dataprovider'
            dataprovider = self.dataprovider
        
        df.dataprovider = dataprovider if dataprovider else df.get_fillvalue()
        #print df.dataprovider

        # MLS Not sure how to handle this, probably shouldn't
        # be directly adding the dynamic property...
        df._add_property('base_dir')
        setattr(df,'base_dir',si.FName['base_dirs'][0])
        #print 'cs path: '+self.name+' base_dir: '+str(self.sensorinfo.FName['base_dirs'])
        for base_dir in si.FName['base_dirs']:
            # If we have /npp1 and /npp1/users in base_dirs, want /npp1/users
            if base_dir and base_dir in self.name and base_dir not in self.base_dir:
                setattr(df,'base_dir',base_dir)

        #log.info('df.ext '+df.ext)
        #print 'StandardDataFileName after DataFileName '+str(df)

        # This is where we actually set the default fields
        # Note df.dataprovider will be overriden in the subclasses if 
        # it is fillvalue. 
        df = self.standard_set_fields(df,wildcards,scifile_obj=scifile_obj)

        # Final filename will NOT have .gz in it. It is automatically 
        # gunzipped in Site.convert
        # If it is tar.gz, it will untar, and final filenames will not match...
        if '.gz' in df.ext and 'tar' not in df.ext:
            df.ext = df.ext.replace('.gz','')
            #log.info('df.ext2 '+df.ext)
        df.sensorinfo = si
        return df

    def create_scratchfile(self,geoips=True):

        #print 'StandardDataFileName create_logfile'
        if self.sensorinfo:
            si = self.sensorinfo
        else:
            si = SatSensorInfo()
        #print si.ScratchFName
        df = DataFileName(path=None,
                nameformat=si.ScratchFName['nameformat'],
                fieldsep=si.ScratchFName['fieldsep'],
                fillvalue=si.ScratchFName['fillvalue'],
                pathnameformat=si.ScratchFName['pathnameformat'],
                pathfieldsep=si.ScratchFName['pathfieldsep'],
                pathfillvalue=si.ScratchFName['pathfillvalue'])
        #print 'StandardDataFileName create_logfile after DataFileName '+str(df)
        dataprovider = None
        if hasattr(self,'dataprovider'):
            dataprovider = self.dataprovider
        df.dataprovider = dataprovider if dataprovider else df.get_fillvalue()
        df = self.standard_set_fields(df)
        df._add_property('pid')
        setattr(df,'pid','pid'+str(os.getpid()))
        df._add_property('timestamp')
        setattr(df,'timestamp','ts'+datetime.utcnow().strftime('%d%H%M%S'))
        df._add_property('subdir')
        setattr(df,'subdir','working')
        return df

    def create_logfile(self,geoips=True):

        #print 'StandardDataFileName create_logfile'
        if self.sensorinfo:
            si = self.sensorinfo
        else:
            si = SatSensorInfo()
        #print si.LogFName
        df = DataFileName(path=None,
                nameformat=si.LogFName['nameformat'],
                fieldsep=si.LogFName['fieldsep'],
                fillvalue=si.LogFName['fillvalue'],
                pathnameformat=si.LogFName['pathnameformat'],
                pathfieldsep=si.LogFName['pathfieldsep'],
                pathfillvalue=si.LogFName['pathfillvalue'])
        #print 'StandardDataFileName create_logfile after DataFileName '+str(df)
        dataprovider = None
        if hasattr(self,'dataprovider'):
            dataprovider = self.dataprovider
        df.dataprovider = dataprovider if dataprovider else df.get_fillvalue()
        df = self.standard_set_fields(df)
        df._add_property('pid')
        setattr(df,'pid','pid'+str(os.getpid()))
        df._add_property('timestamp')
        setattr(df,'timestamp','ts'+datetime.utcnow().strftime('%d%H%M%S'))
        df.ext = 'log'
        if geoips:
            df.prefix = 'GW'
        else:
            df.prefix = 'PW'
        df.qsubname = df.prefix+df.dataprovider
        # Beryl fails if -N is longer than 15 characters
        df.qsubname = df.qsubname[0:14]
        return df

    def get_datetime(self):
        return self.datetime


    def standard_set_fields(self,df,wildcards=False,scifile_obj=None):
        #print 'StandardDataFileName standard_set_fields'
        dfn = self.set_fields(df,wildcards,scifile_obj)
        if hasattr(dfn,'extra'):
            df.extra = dfn.extra.replace('.','p')
        return dfn

    def set_fields(self,df,wildcards=False,scifile_obj=None):
        if not scifile_obj:
            df.date = self.date
            df.time = self.time
            df.satname = self.satname
            df.sensorname = self.sensorname
            df.ext = self.ext
        else:
            df.datetime = scifile_obj.start_datetime
            dt_strs = df.set_datetime_str(scifile_obj.start_datetime) 
            for dt_field in dt_strs.keys():
                setattr(df,dt_field,dt_strs[dt_field])
            df.satname = scifile_obj.platform_name
            df.sensorname = scifile_obj.source_name
            df.ext = 'h5'
        # set in create_standard()
        #df.dataprovider = self.dataprovider 
        df.scifile_source = df.sensorname
        df.resolution = self.resolution
        df.channel = self.channel
        df.producttype = self.producttype
        df.area = self.area
        df.extra = self.extra
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')
        return df

    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default), use that class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie )
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'StandardDataFileName istype'
        return True

class ABIFileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie AHIDATFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype abidat'
        #print self.hs
        #print self.ext
        #print self.satname.lower()
        #print self.sensorinfo.satname
        # self.satname is from filename, self.sensorinfo is current attempt at matching format
        try:
            sensor,level,datatype,chan = self.sensornamelevelprodtypescantype.split('-')
        except ValueError:
            sensor,level,datatype = self.sensornamelevelprodtypescantype.split('-')
        if self.satname in ['G16','G17'] and sensor in ['ABI','SUVI','EXIS','SEIS','MAG','GLM']:
            if self.satname == 'G16' and self.sensorinfo.satname == 'G16':
                return True
            elif self.satname == 'G17' and self.sensorinfo.satname == 'G17':
                return True
            else:
                return False
        else:
            return False


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        # From utils.satellite_info.AHISensorInfo:
        # OR_ABI-L1b-RadF-M3C02_G16_s20170642036100_e20170642046467_c20170642046500.nc
        # <or>_<sensornamelevelprodtypescantype>_<level>_<prodtype>_<scantype>_<satname>_<date{s%Y%m%d%H%M%S}>_<enddt{e%Y%m%d%H%M%S}>_<createdt{c%Y%m%d%H%M%S}>

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = self.sensorinfo.geoips_satname
        df.resolution = self.get_fillvalue()
        try:
            sensor,level,datatype,chan = self.sensornamelevelprodtypescantype.split('-')
        except ValueError:
            chan = None
            sensor,level,datatype = self.sensornamelevelprodtypescantype.split('-')
        df.sensorname = sensor.lower()
        df.scifile_source = df.sensorname
        if chan:
            chan = 'B'+chan[3:5]
            df.channel = chan
        else:
            df.channel = datatype
        df.producttype = level
        df.area = datatype
        df.extra = self.get_fillvalue()
        df.ext = self.ext
        # LAME add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df

class AHIDATFileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie AHIDATFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype ahidat'
        #print self.hs
        #print self.ext
        #print self.satname.lower()
        #print self.sensorinfo.satname
        # self.satname is from filename, self.sensorinfo is current attempt at matching format
        if self.hs == 'HS':
            return True
        else:
            return False


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        # From utils.satellite_info.AHISensorInfo:
        # 20150617_0250/HS_H08_20150617_0250_B12_FLDK_R20_S0510.DAT.bz2
        #<hs>_<satname>_<date{%Y%m%d}>_<time{%H%M}>_<channel>_<scansize>_<resolution>_<slice>'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = self.sensorinfo.satname
        df.sensorname = self.sensorinfo.sensorname
        df.scifile_source = df.sensorname
        df.resolution = self.resolution
        df.channel = self.channel
        df.producttype = self.slice
        df.area = self.scansize+'_'+self.slice
        df.extra = self.get_fillvalue()
        df.ext = self.ext
        # LAME add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df

class AHIHPCtgzFileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie AHIHPCtgzFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype seviri'
        #print self.satname.lower()
        #print self.sensorinfo.satname
        # self.satname is from filename, self.sensorinfo is current attempt at matching format
        if self.ext == 'tar.gz':
            return True
        else:
            return False


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        #RNSCA-RVIRS_npp_d20141205_t0012213_e0013467_b16083_c20141205020902820922_noaa_ops.h5
        # From utils.satellite_info.VIIRSSensorInfo:
        #<datatype>_<satname>_<date{d%Y%m%d}>_<time{t%H%M%S%f}>_<endtime>_<orbitnum>_<creationtime>_<dataoriginator>_<datalevel>'
        #print 'setting npp fields'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = self.sensorinfo.satname
        df.sensorname = self.sensorinfo.sensorname
        df.scifile_source = df.sensorname
        if wildcards:
            df.resolution = self.get_fillvalue()
            df.channel = self.get_fillvalue()
            df.area = self.get_fillvalue()
        else:
            df.resolution = 'all'
            df.channel = 'all'
            df.area = 'all'
        df.producttype = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext
        # add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df

class AMSR2FileName(StandardDataFileName):

    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie AMSR2FileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in amsr2 istype'
        if 'AMSR2' in self.amsr2prod:
            return True
        else:
            return False

    def set_fields(self,df,wildcards=False,scifile_obj=None):

        #print 'in GPM set_fields'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.sensorname = self.sensorinfo.sensorname
        df.satname = self.sensorinfo.satname
        df.scifile_source = df.sensorname
        #df.dataprovider = 'local' if df.dataprovider is df.get_fillvalue() else df.get_fillvalue()
        # Sometimes AMSR2-SEAICE-NH, sometimes AMSR2-MBT
        vals = self.amsr2prod.lower().split('-')
        df.producttype = vals[1]

        df.resolution = df.get_fillvalue()
        df.channel = df.get_fillvalue()
        df.area = df.get_fillvalue()
        df.ext = self.ext
        df.extra = self.endtime+'_'+self.creationtime

        return df

class AMSUFileName(StandardDataFileName):
    '''Subclass of StandardDataFileName specifically for AMSU.  Allows
    for easy conversion of AMSU date formats.
    NPR.AAOP.NN.D13344.S1426.E1614.B4409596.NS
    NPR.MHOP.M1.D13344.S1703.E1758.B0637980.NS
    3rd field: NK NOAA-15
                NL NOAA-16
                NM NOAA-17
                NN NOAA-18
                NP NOAA-19
                M2 METOP-2/A
    2nd field:  AAOP: AMSU-A
                ABOP: AMSU-B
                MHOP: AMSU-B
    '''

    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie AMSUFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print ''
        #print 'fnstr: '+self.name
        #print 'file sensor: '+self.sensor
        #print 'file satellite: '+self.satellite
        self.standardsensorname = 'NONE'
        self.standardsatname = 'NONE'
        if self.sensor in ['AAOP']:
            self.standardsensorname = 'amsua'
        elif self.sensor in ['ABOP','MHOP']:
            self.standardsensorname = 'amsub'

        if self.satellite == 'NK': self.standardsatname = 'n15'
        elif self.satellite == 'NL': self.standardsatname = 'n16'
        elif self.satellite == 'NM': self.standardsatname = 'n17'
        elif self.satellite == 'NN': self.standardsatname = 'n18'
        elif self.satellite == 'NP': self.standardsatname = 'n19'
        elif self.satellite == 'M2': self.standardsatname = 'm2a'
        #print 'file sensor: '+self.standardsensorname
        #print 'file satellite: '+self.standardsatname
        #print 'checking: '+self.sensorinfo.sensorname
        #print 'checking: '+self.sensorinfo.satname
        # Check the sat/sensor we are currently trying against what it matches in the filename
        if self.standardsensorname == self.sensorinfo.sensorname and self.standardsatname == self.sensorinfo.satname:
            return True
        else:
            return False

    def getconverter(self):
        if self.standardsensorname == 'amsua':
            return os.getenv('SATBIN')+'/amsua2tdf'
        elif self.standardsensorname == 'amsub':
            return os.getenv('SATBIN')+'/amsub2tdf'
        else:
            return None


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        # From utils.satellite_info.VIIRSSensorInfo:
        #<datatype>_<satname>_<date{d%Y%m%d}>_<time{t%H%M%S%f}>_<endtime>_<orbitnum>_<creationtime>_<dataoriginator>_<datalevel>'
        #print 'setting npp fields'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])

        # MLS SAME THING IS HERE AND IN ISTYPE! consolidate.
        if self.sensor in ['AAOP']:
            df.sensorname = 'amsua'
        elif self.sensor in ['ABOP','MHOP']:
            df.sensorname = 'amsub'
        df.scifile_source = df.sensorname

        if self.satellite == 'NK': df.satname = 'n15'
        elif self.satellite == 'NL': df.satname = 'n16'
        elif self.satellite == 'NM': df.satname = 'n17'
        elif self.satellite == 'NN': df.satname = 'n18'
        elif self.satellite == 'NP': df.satname = 'n19'
        elif self.satellite == 'M2': df.satname = 'm2a'
        df.resolution = self.get_fillvalue()
        df.channel = self.get_fillvalue()
        df.producttype = self.get_fillvalue()
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext
        # LAME add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df

class AMSUTDFFileName(StandardDataFileName):

    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie AMSUTDFFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in amsutdf istype'
        #print self.satellite
        #print self.sensorinfo.satname
        #print self.sensor
        #print self.sensorinfo.sensorname
        if self.satellite == self.sensorinfo.satname and self.sensor == self.sensorinfo.sensorname:
            return True
        else:
            return False

    def set_fields(self,df,wildcards=False,scifile_obj=None):

        #print 'in GPM set_fields'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.sensorname = self.sensorinfo.sensorname
        df.satname = self.sensorinfo.satname
        df.scifile_source = df.sensorname
        #df.dataprovider = 'local' if df.dataprovider is df.get_fillvalue() else df.get_fillvalue()
        df.producttype = self.get_fillvalue()
        df.resolution = df.get_fillvalue()
        df.channel = df.get_fillvalue()
        df.area = df.get_fillvalue()
        df.ext = 'tdf'
        df.extra = df.get_fillvalue()

        return df

class ASCATFileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie ASCATFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        # self.satname is from filename, self.sensorinfo is current attempt at matching format
        if self.satname.lower() in self.sensorinfo.satname:
            return True
        else:
            return False


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        # pull/ascat_20150628_232700_metopb_14410_srv_o_125_ovw.l2_bin
        # From utils.satellite_info.ASCATSensorInfo:
        #'ascat_<date{%Y%m%d}>_<time{%H%M%S}>_<satname>_<num1>_<srv>_<o>_<res>_<ovw>'
        #print 'setting ascat fields'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = self.sensorinfo.satname
        df.sensorname = self.sensorinfo.sensorname
        df.scifile_source = df.sensorname
        df.resolution = self.res[0:2]+'p'+self.res[2]+'km'
        df.channel = self.get_fillvalue()
        df.producttype = self.get_fillvalue()
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext
        # add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df

class FNMOCBFTGSFileName(StandardDataFileName):
    '''Subclass of datetime specifically for msg and mtsat GeoSimple files from FNMOC.  Allows
    for easy conversion of METEOSAT GS date formats.
    SSMI TDF:   data: US058SORB-DEFspp.tdrmi_f13_d20050810_s113500_e132000_r53574_cfnoc.def
    SSMIS SDR:  data: US058SORB-RAWspp.sdris_f16_d20050810_s095537_e114116_r09348_cfnoc.raw
    SSMIS EDR:  data: US058SORB-RAWspp.envis_f16_d20050810_s095537_e114116_r09348_cfnoc.raw
    WS EDR68:
    WS SDR68:   data: US058SORB-BINspp.wndmi_fws_d20050806_s115305_e152502_r13375_cfnmoc.sdr68
    WS SDR187:  data: US058SORB-BINspp.wndmi_fws_d20050806_s115305_e152502_r13375_cfnmoc.sdr187
    WS IDR37:
    DMSP OLS:   data: f16_3091538_DS.DAT
    METEOSAT8:  data: ME8_2201700_M8.DAT geoloc: ME8_2201700_PL.DAT
    METEOSAT9:  data: ME9_2201700_M9.DAT geoloc: ME9_2201700_PL.DAT
    METEOSAT10: data: ME0_2201700_M0.DAT geoloc: ME0_2201700_PL.DAT
       MTSAT1:  data: MT1_2671532_MT.DAT geoloc: MT1_2671532_TA.DAT
       MTSAT2:  data: MT2_2671532_MT.DAT geoloc: MT2_2671532_TA.DAT'''

    def set_filetype(self):
        if self.sensorinfo.satname in ['mt1','mt2']:
            self.geo_simple_var_list = ''
            self.geo_simple_cmd = os.getenv('SATBIN')+'/geo_simple_'+self.satname.upper()
        elif self.sensorinfo.satname in ['me10','me8','me9']:
            self.geo_simple_var_list = ''
            self.geo_simple_cmd = os.getenv('SATBIN')+'/geo_simple_ME0'

        if self.producttype in ['TA','PL']:
            self.filetype = 'geoloc'
        elif self.producttype in ['MT','M0','M8','M9']:
            self.filetype = 'data'

    def switch_type(self):
        other_dfn = DataFileName(self.name)
        other_dfn.set_filetype()
        log.info('self.filetype: '+self.filetype+' dtother.filetype: '+other_dfn.filetype)
        log.info('sdfn.producttype: '+self.producttype+' other_sdfn.producttype: '+other_dfn.producttype)
        if self.filetype == 'geoloc':
            other_dfn.filetype = 'data'
            if self.producttype == 'TA':
                other_dfn.producttype = 'MT'
            elif self.sensorinfo.satname == 'me10':
                other_dfn.producttype = 'M0'
            elif self.sensorinfo.satname == 'me8':
                other_dfn.producttype = 'M8'
            elif self.sensorinfo.satname == 'me9':
                other_dfn.producttype = 'M9'
            log.info('geoloc sdfn.filetype: '+self.filetype+' other_sdfn.filetype: '+other_dfn.filetype)
            log.info('sdfn.producttype: '+self.producttype+' other_sdfn.producttype: '+other_dfn.producttype)
        elif self.filetype == 'data':
            other_dfn.filetype = 'geoloc'
            if self.sensorinfo.satname in ['mt1','mt2']:
                other_dfn.producttype = 'TA'
            elif self.sensorinfo.satname in ['me10','me8','me9']:
                other_dfn.producttype = 'PL'
            log.info('data sdfn.filetype: '+self.filetype+' other_sdfn.filetype: '+other_dfn.filetype)
            log.info('sdfn.producttype: '+self.producttype+' other_sdfn.producttype: '+other_dfn.producttype)
        return other_dfn
        
    def geoloc_and_data_exist(self):
        self.set_filetype()
        other_dfn = self.switch_type()
        other_sdfn = other_dfn.create_standard()
        sdfn = self.create_standard()
        if self.filetype == 'geoloc':
            geoloc_file = os.path.dirname(sdfn.name)+'/'+self.origfnstr()
            data_file = os.path.dirname(other_sdfn.name)+'/'+other_dfn.origfnstr()
        else:
            geoloc_file = os.path.dirname(sdfn.name)+'/'+other_dfn.origfnstr()
            data_file = os.path.dirname(other_sdfn.name)+'/'+self.origfnstr()
        log.info('data file: '+data_file+' geoloc file: '+geoloc_file)
        if os.path.exists(data_file):
            log.info('data_file exists '+data_file)
        if os.path.exists(geoloc_file):
            log.info('geoloc_file exists: '+geoloc_file)
        if os.path.exists(data_file) and os.path.exists(geoloc_file):
            log.info('both files exist')
            return data_file,geoloc_file
        return None,None

    # MLS LOOK AT AMSU istype!!! Should use that here, but don't want to 
    # spend time on it right now.  Should be able to determine sat/sensor 
    # before opening, only "istype" if sat/sensor we are trying matches the
    # dictionary of filename sats/sensors to satellite_info sat/sensors.
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie FNMOCBFTGSName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype fnmocbftgs'
        #print self.satname.lower()
        #print self.sensorinfo.satname
        #print self.ext.lower()
        # self.satname is from filename, self.sensorinfo is current attempt at matching format
        if self.satname.lower() in self.sensorinfo.satname and self.ext.lower() == 'dat':
            return True
        # me10 is listed as me0 in filename
        elif self.satname.lower() == 'me0' and self.sensorinfo.satname == 'me10' and self.ext.lower() == 'dat':
            return True
        else:
            return False

    def origfnstr(self):
        return self.satname.upper()+'_'+self.datetime.strftime('%j%H%M')+'_'+self.producttype+'.DAT'


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        # From utils.satellite_info.VIIRSSensorInfo:
        #<datatype>_<satname>_<date{d%Y%m%d}>_<time{t%H%M%S%f}>_<endtime>_<orbitnum>_<creationtime>_<dataoriginator>_<datalevel>'
        #print 'setting npp fields'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = self.sensorinfo.satname
        df.sensorname = self.sensorinfo.sensorname
        df.scifile_source = df.sensorname
        df.resolution = self.get_fillvalue()
        df.channel = self.get_fillvalue()
        df.producttype = self.producttype.lower()
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext
        # add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df

class GPMFileName(StandardDataFileName):

    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie GPMFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in gpm istype'
        #shell()
        if self.satname.lower() == 'gpm' or self.satname.lower() == 'ms':
            return True
        else:
            return False

    def set_fields(self,df,wildcards=False,scifile_obj=None):

        #print 'in GPM set_fields'

        # See utils/satellite_info.py for these fields
        #print self.SYYYYJJJ[1:8]
        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        #print dt
        #dt = datetime.strptime(self.YYYYMMDD+self.HHMN,'%Y%m%d%H%M')
        #df.date = dt.strftime('%Y%m%d')
        #df.time = self.HHMN
        df.sensorname = self.sensorinfo.sensorname
        df.satname = self.sensorinfo.satname
        df.scifile_source = df.sensorname
        #df.dataprovider = 'local' if df.dataprovider is df.get_fillvalue() else df.get_fillvalue()
        df.producttype = self.product
        df.resolution = df.get_fillvalue()
        if 'DPRGMI' == self.sensorname:
            df.channel = 'precip'
        elif 'DPR' in self.product or 'DPR' in self.sensorname:
            df.channel = 'dpr'
        elif 'TB' in self.product:
            df.channel = 'gmi'
        elif 'GPROF' in self.product:
            df.channel = 'gprof'
        elif 'HHR-E' in self.level:
            df.channel = 'imerg_early'
        elif 'HHR-L' in self.level:
            df.channel = 'imerg_late'
        df.area = df.get_fillvalue()
        rt,df.ext = self.exttype.lower().split('-')
        df.extra = self.product+'_'+self.level.lower()+'_'+self.version.lower()

        return df

class CLAVRXFileName(StandardDataFileName):

    def istype(self):
        '''
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName),
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie GOESFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype'
        if self.satname in ['goes15']:
            return True
        else:
            return False

    def set_fields(self,df,wildcards=False,scifile_obj=None):

        #print 'in CLAVRXFileName set_fields'
        #See utils/satellite_info.py for these fields
        #goes15_2016_310_1800.level2.hdf
        #'<satname>_<date{%Y}>_<doy{%j}>_<time{%H%M}.<level>'
        
        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        #print dt
        #dt = datetime.strptime(self.YYYYMMDD+self.HHMN,'%Y%m%d%H%M')
        #df.date = dt.strftime('%Y%m%d')
        #df.time = self.HHMN
        df.sensorname = 'clavrx'
        df.satname = self.satname
        df.scifile_source = df.sensorname
        df.dataprovider = 'local' if df.dataprovider is df.get_fillvalue() else df.get_fillvalue()
        df.producttype = self.get_fillvalue()
        df.resolution = self.get_fillvalue()
        df.channel = self.get_fillvalue()
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext

        return df

class CCBGFileName(StandardDataFileName):

    def istype(self):
        '''
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName),
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie GOESFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype'
        if self.satname in ['goes15']:
            return True
        else:
            return False

    def set_fields(self,df,wildcards=False,scifile_obj=None):

        #print 'in CLAVRXFileName set_fields'
        #See utils/satellite_info.py for these fields
        #goes15_2016_310_1800.level2.hdf
        #'<satname>_<date{%Y}>_<doy{%j}>_<time{%H%M}.<level>'
        
        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        #print dt
        #dt = datetime.strptime(self.YYYYMMDD+self.HHMN,'%Y%m%d%H%M')
        #df.date = dt.strftime('%Y%m%d')
        #df.time = self.HHMN
        df.sensorname = 'ccbg'
        df.satname = self.satname
        df.scifile_source = df.sensorname
        df.dataprovider = 'local' if df.dataprovider is df.get_fillvalue() else df.get_fillvalue()
        df.producttype = self.get_fillvalue()
        df.resolution = self.get_fillvalue()
        df.channel = self.get_fillvalue()
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext

        return df

class GOESFileName(StandardDataFileName):

    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie GOESFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype'
        if self.satname in ['g13','g14','g15']:
            return True
        else:
            return False

    def set_fields(self,df,wildcards=False,scifile_obj=None):

        #print 'in GoesFileName set_fields'

        # See utils/satellite_info.py for these fields
        #print self.SYYYYJJJ[1:8]
        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        #print dt
        #dt = datetime.strptime(self.YYYYMMDD+self.HHMN,'%Y%m%d%H%M')
        #df.date = dt.strftime('%Y%m%d')
        #df.time = self.HHMN
        df.sensorname = self.sensorinfo.sensorname
        df.satname = self.sensorinfo.satname
        df.scifile_source = df.sensorname
        df.dataprovider = 'local' if df.dataprovider is df.get_fillvalue() else df.get_fillvalue()
        df.producttype = 'sdr'
        if hasattr(self,'dataset'):
            df.resolution = self.dataset
        else:
            df.channel = 'all'
        if hasattr(self,'band'):
            df.channel = self.band
        else:
            df.channel = 'all'
        if self.satname in ['g15']:
            df.area = 'goes-west'
        elif self.satname in ['g13']:
            df.area = 'goes-east'
        elif self.satname in ['g14']:
            df.area = 'goes-south'
        else:
            raise ValueError('Unknown GOES satellite encountered.')
        df.extra = self.get_fillvalue()
        df.ext = self.ext

        return df

class GOESCLASSFileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie GOESCLASSFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype'
        if self.satname in ['goes13','goes14','goes15']:
            return True
        else:
            return False

    def set_fields(self,df,wildcards=False,scifile_obj=None):

        # See utils/satellite_info.py for these fields
        #print self.SYYYYJJJ[1:8]
        self.date = self.year+self.doy
        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        #print dt
        #dt = datetime.strptime(self.YYYYMMDD+self.HHMN,'%Y%m%d%H%M')
        #df.date = dt.strftime('%Y%m%d')
        #df.time = self.HHMN
        df.sensorname = self.sensorinfo.sensorname
        df.satname = self.sensorinfo.satname
        df.scifile_source = df.sensorname
        df.dataprovider = 'local' if df.dataprovider is df.get_fillvalue() else df.get_fillvalue()
        df.producttype = 'sdr'
        df.resolution = 'all'
        if hasattr(self,'band'):
            df.channel = self.band
        else:
            df.channel = 'all'
        if self.satname in ['goes15', 'g15']:
            df.area = 'goes-west'
        elif self.satname in ['goes13', 'g13']:
            df.area = 'goes-east'
        elif self.satname in ['goes14', 'g14']:
            df.area = 'goes-south'
        else:
            raise ValueError('Unknown GOES satellite encountered.')
        df.extra = self.get_fillvalue()
        df.ext = self.ext

        return df

class JAMIBFTTDFXFileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie JAMIBFTTDFXFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype seviri'
        #print self.satname.lower()
        #print self.sensorinfo.satname
        # self.satname is from filename, self.sensorinfo is current attempt at matching format
        if self.satname.lower() in self.sensorinfo.satname and self.ext == 'tdfx':
            return True
        else:
            return False


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        #RNSCA-RVIRS_npp_d20141205_t0012213_e0013467_b16083_c20141205020902820922_noaa_ops.h5
        # From utils.satellite_info.VIIRSSensorInfo:
        #<datatype>_<satname>_<date{d%Y%m%d}>_<time{t%H%M%S%f}>_<endtime>_<orbitnum>_<creationtime>_<dataoriginator>_<datalevel>'
        #print 'setting npp fields'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = self.sensorinfo.satname
        df.sensorname = self.sensorinfo.sensorname
        df.scifile_source = df.sensorname
        df.resolution = self.get_fillvalue()
        df.channel = self.get_fillvalue()
        df.producttype = self.get_fillvalue()
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext
        # LAME add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df

class JAMITDFFileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie JAMITDFFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype seviri'
        #print self.satname.lower()
        #print self.sensorinfo.satname
        # self.satname is from filename, self.sensorinfo is current attempt at matching format
        if self.satname.lower() in self.sensorinfo.satname and self.ext == '':
            return True
        else:
            return False


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        #RNSCA-RVIRS_npp_d20141205_t0012213_e0013467_b16083_c20141205020902820922_noaa_ops.h5
        # From utils.satellite_info.VIIRSSensorInfo:
        #<datatype>_<satname>_<date{d%Y%m%d}>_<time{t%H%M%S%f}>_<endtime>_<orbitnum>_<creationtime>_<dataoriginator>_<datalevel>'
        #print 'setting npp fields'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = self.sensorinfo.satname
        df.sensorname = self.sensorinfo.sensorname
        df.scifile_source = df.sensorname
        df.resolution = self.get_fillvalue()
        df.channel = self.get_fillvalue()
        df.producttype = self.get_fillvalue()
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext
        # LAME add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df

class ICAPFileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie MEgha..FileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        if hasattr(self,'icap') and 'icap' in self.icap:
            return True
        else:
            return False


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        # /shared/aerosol_maud1/users/sessions/products/ICAP/201711/
        # icap_2017110500_aod.nc
        # OrigFName['nameformat'] = '<icap>_<date%Y%m%d%H>_<prod>'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = self.sensorinfo.satname
        df.sensorname = self.sensorinfo.sensorname
        df.scifile_source = df.sensorname
        df.resolution = self.get_fillvalue()
        df.channel = self.get_fillvalue()
        df.producttype = self.prod
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext
        # LAME add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df

class MeghaTropiquesFileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie MEgha..FileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        if 'MT1SAP' in self.satsensorlevel:
            return True
        else:
            return False


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        # From utils.satellite_info.SAPHIRSensorInfo:
        # MT1SAPSL1A__1.07_000_1_17_I_2015_08_31_05_13_46_2015_08_31_07_07_31_20047_20049_207_66_68_BL1_00.h5
        #OrigFName['nameformat']='<satsensorlevel>_<blank>_<vers>_<num1>_<num2>_<num3>_'+\
        #                        '<let1>_<dt0{%Y}>_<dt1{%m}>_<dt2{%d}>_'+\
        #                        '<dt3{%H}>_<dt4{%M}>_<dt5{%S}>_<enddate1>'+\
        #                        '_<enddate2>_<enddate3>_<endtime1>_<endtime2>_'+\
        #                        '<endtime3>_<num4>_<num5>_<num6>_<num7>_'+\
        #                        '<num8>_<let2>_<num9>'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = self.sensorinfo.satname
        df.sensorname = self.sensorinfo.sensorname
        df.scifile_source = df.sensorname
        df.resolution = self.get_fillvalue()
        df.channel = self.get_fillvalue()
        df.producttype = self.satsensorlevel
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext
        # LAME add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df

###################################################
###################################################
###################################################
###################################################
###################################################
###################################################
class MODISFileName(StandardDataFileName):

    def set_fields(self,df,wildcards=False,scifile_obj=None):

        #print 'set_fields in MODISFileName'

        # See utils/satellite_info.py for these fields
        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        if 'MYD' in self.datatype or 'P' in self.datetime_fields['time']:
            df.satname = 'aqua'
        elif 'MOD' in self.datatype or 'A' in self.datetime_fields['time']:
            df.satname = 'terra'
        df.sensorname = 'modis'
        df.scifile_source = df.sensorname
        df.dataprovider = 'lance' if df.dataprovider is df.get_fillvalue() else df.dataprovider

        # Could change to this in the future, once old GeoIPS turned off
        #if 'myd' in df.producttype:
        #    df.producttype = df.producttype.replace('myd','mod') 
        #df.resolution = self.datatype.lower()[5:]
        #if not df.resolution:
        #    df.resolution = self.get_fillvalue()
        #df.producttype = self.datatype.lower()[0:5]

        # Backwards compatibility with old GeoIPS
        df.producttype = self.get_fillvalue()
        df.resolution = self.get_fillvalue()
        df.channel = self.datatype
        if 'MYD' in df.channel:
            df.channel = df.channel.replace('MYD','MOD')

        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext

        return df

class SSMISRawFileName(StandardDataFileName):

    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie NAVGEMFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype'

        if 'US058SORB' in self.stuff1:
            return True
        else:
            return False

    def set_fields(self,df,wildcards=False,scifile_obj=None):

        #print 'in GoesFileName set_fields'

        # See utils/satellite_info.py for these fields
        #print self.SYYYYJJJ[1:8]
        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        #print dt
        #dt = datetime.strptime(self.YYYYMMDD+self.HHMN,'%Y%m%d%H%M')
        #df.date = dt.strftime('%Y%m%d')
        #df.time = self.HHMN
        df.sensorname = 'ssmis'
        df.satname = self.satname.lower()
        df.scifile_source = df.sensorname
        if self.dataprovider.lower() == 'cfnoc':
            df.dataprovider = 'cfnoc'
        else:
            df.dataprovider = 'fnmoc' if df.dataprovider is df.get_fillvalue() else df.get_fillvalue()
        df.producttype = self.get_fillvalue()
        df.resolution = self.get_fillvalue()
        df.channel = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.area = self.get_fillvalue()
        df.ext = 'grb'

        return df

class NAVGEMGribFileName(StandardDataFileName):

    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie NAVGEMFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype'

        if 'US058GMET' in self.stuff1 or 'US058GOCN' in self.stuff1 \
                or 'US058GLND' in self.stuff1 or 'US058GCOM' in self.stuff1:
            return True
        else:
            return False

    def set_fields(self,df,wildcards=False,scifile_obj=None):

        #print 'in NAVGEMFileName set_fields'
        # US058GCOM-GR1mdl.0018_0056_03300F0OF2017020206_0001_000000-000000grnd_sea_temp
        # US058GCOM-GR1dyn.COAMPS-NEPAC_NEPAC-n2-a1_01800F0NL2017010112_0001_000000-000000grnd_sea_temp

        # See utils/satellite_info.py for these fields
        #print self.SYYYYJJJ[1:8]
        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        #print dt
        #dt = datetime.strptime(self.YYYYMMDD+self.HHMN,'%Y%m%d%H%M')
        #df.date = dt.strftime('%Y%m%d')
        #df.time = self.HHMN
        #df.sensorname = 'model'
        #df.satname = 'model'
        #df.scifile_source = df.sensorname
        #df.dataprovider = 'godae' if df.dataprovider is df.get_fillvalue() else df.get_fillvalue()
        df.dataprovider = 'godae'
        df.producttype = self.product1[13:]
        if hasattr(self,'product2'):
            df.producttype += '_'+self.product2
        if hasattr(self,'product3'):
            df.producttype += '_'+self.product3
        if hasattr(self,'product4'):
            df.producttype += '_'+self.product4
        if hasattr(self,'product5'):
            df.producttype += '_'+self.product5
        df.resolution = 'tau'+self.date[0:3]
        if 'COAMPS' in self.stuff1:
            df.sensorname = 'coamps'
            df.satname = 'model'
            df.scifile_source = df.sensorname
            df.channel = 'coamps'
        elif 'GR1mdl' in self.stuff1:
            df.sensorname = 'navgem'
            df.satname = 'model'
            df.scifile_source = df.sensorname
            df.channel = 'navgem'
        else:
            df.channel = 'unknownmodel'
        df.extra = 'lev'+self.product1.split('-')[0]
        parts = self.stuff1.split('-')
        if len(parts) == 3 and parts[2] in ['NWATL','NEPAC','SOCAL','EURO','EQAM']:
            df.area = parts[2].lower()
        elif len(parts) == 2:
            df.area = 'global'
        else:
            df.area = 'unknownarea'
        df.ext = 'grb'

        return df

class NAVGEMFileName(StandardDataFileName):

    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie NAVGEMFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype'
        resolution = self.resolution.split('x')

        if len(resolution) == 2 and resolution[0].isdigit() and resolution[1].isdigit():
            return True
        else:
            return False

    def set_fields(self,df,wildcards=False,scifile_obj=None):

        #print 'in GoesFileName set_fields'

        # See utils/satellite_info.py for these fields
        #print self.SYYYYJJJ[1:8]
        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        #print dt
        #dt = datetime.strptime(self.YYYYMMDD+self.HHMN,'%Y%m%d%H%M')
        #df.date = dt.strftime('%Y%m%d')
        #df.time = self.HHMN
        df.sensorname = self.sensorinfo.sensorname
        df.satname = self.sensorinfo.satname
        df.scifile_source = df.sensorname
        df.dataprovider = 'local' if df.dataprovider is df.get_fillvalue() else df.get_fillvalue()
        df.producttype = 'sdr'
        df.resolution = 'all'
        df.channel = 'all'
        df.extra = self.get_fillvalue()
        df.area = df.get_fillvalue()
        df.ext = self.ext

        return df


class NPPFileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie NPPFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in npp istype'
        #print self.datatype
        #print self.sensorinfo.all_prefixes
        #shell()
        # datatypee is sdr for legacy viirs tdfs from beryl/old GeoIPS
        if self.datatype in self.sensorinfo.all_prefixes or \
           self.datatype in ['VNP02IMG', 'VNP02MOD', 'VNP02DNB', 'VNP03DNB', 'VNP03MOD', 
                             'VNP03IMG',
                             'VJ102IMG', 'VJ102MOD', 'VJ102DNB', 'VJ103DNB', 'VJ103MOD',
                             'VJ103IMG']:
            return True
        else:
            return False

    def set_fields(self,df,wildcards=False,scifile_obj=None):
        #RNSCA-RVIRS_npp_d20141205_t0012213_e0013467_b16083_c20141205020902820922_noaa_ops.h5
        # From utils.satellite_info.VIIRSSensorInfo:
        #<datatype>_<satname>_<date{d%Y%m%d}>_<time{t%H%M%S%f}>_<endtime>_<orbitnum>_<creationtime>_<dataoriginator>_<datalevel>'
        #print 'setting npp fields'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = self.sensorinfo.satname
        df.sensorname = self.sensorinfo.sensorname
        df.scifile_source = df.sensorname
        default_dp = 'x'
        if hasattr(self,'dataoriginator') and hasattr(self,'datalevel'):
            default_dp = self.dataoriginator+'_'+self.datalevel
        # For legacy filenames (old GeoIPS) from beryl
        elif hasattr(self,'dataoriginator_datalevel'):
            default_dp = self.dataoriginator_datalevel
        #print df.dataprovider
        #print default_dp
        df.dataprovider = default_dp if df.dataprovider is self.get_fillvalue() else df.dataprovider+'_'+default_dp
        #print df.dataprovider
        df.resolution = self.get_fillvalue()
        df.channel = self.datatype
        df.producttype = ''
        for prodtype in self.sensorinfo.prefixes.keys():
            if self.datatype in self.sensorinfo.prefixes[prodtype]: 
                df.producttype += prodtype
        if not df.producttype:
            if self.datatype in ['VNP03DNB','VNP03IMG','VNP03MOD', 'VNP02DNB', 'VNP02IMG', 
                                 'VNP02MOD',
                                 'VJ102IMG', 'VJ102MOD', 'VJ102DNB', 'VJ103DNB', 'VJ103MOD',
                                 'VJ103IMG']:
                df.producttype = 'sdr'
            else:
                df.producttype = self.get_fillvalue()
        df.area = self.get_fillvalue()
        if self.datatype == 'RNSCA-RVIRS':
            # LAME using this so we can recreate the original filename before 
            # running CSPP (it needs original filename).  We want to use our 
            # filenames to store the data to maintain dataprovider information.
            # NEED DATABASE.
            df.extra = self.datatype+'_'+self.satname+'_'+self.date+'_'+self.time+'_'+self.endtime+'_'+self.orbitnum+'_'+self.creationtime+'_'+self.dataoriginator+'_'+self.datalevel
        else:
            if hasattr(self,'orbitnum') and hasattr(self,'creationtime'):
                df.extra = self.orbitnum+'_'+self.creationtime
            # BERYL ATMS does not have creationtime...
            elif hasattr(self,'orbitnum'):
                df.extra = self.orbitnum+'_'+self.time+'_'+self.endtime
            # Legacy old GeoIPS tdfs from beryl already have extra set.
            elif hasattr(self,'endorbitcreationtime'):
                df.extra = self.endorbitcreationtime

        df.ext = self.ext
        # LAME add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df


class OSCATKNMI25FileName(StandardDataFileName):

    def istype(self):
        '''
        istype method is called after successfully matching a filename
        format.  If istype returns True (default), use that class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie RSCATFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        if self.oscat == 'oscat' and self.level == 'l2':
            return True
        else:
            return False

    # Return our standard filenaming convention, from parsing orig fname format
    def set_fields(self,df,wildcards=False,scifile_obj=None):
        # oscat_20170913_102336_scasa1_05107_o_250_2104_ovw_l2.nc
        # from utils.satellite_info.OSCATensorInfo:
        # <oscat>_<date{%Y%m%d}>_<time{%H%M%S}>_<shortsat>_<rev>_<type>_<resolution>_<vers>_<cont>_<level>
        df.date = self.date
        df.time = self.time
        df.datetime = self.datetime
        df.satname = 'scatsat-1'
        df.sensorname = 'oscat'
        df.scifile_source = df.sensorname
        df.dataprovider = 'KNMI'
        df.resolution = '25p0km'
        df.channel = self.get_fillvalue()
        df.producttype = self.get_fillvalue()
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext

        return df


class RSCAT25FileName(StandardDataFileName):

    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default), use that class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie RSCAT25FileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        if 'RS_S2B' in self.RS_datatyperevnum: 
            return True
        else:
            return False

    def get_revlist_fnames(self):
        fnamedt =  self.datetime
        nowdt = datetime.utcnow()
        prevdt = nowdt - timedelta(hours=1)
        fnamedt2 = fnamedt + timedelta(hours=1)
        revlistdir = os.getenv('SATDATROOT')+'/scat/rscat/revlists'
        revlistfnames = [revlistdir+nowdt.strftime('/revlist%Y%m%d.%H.csv'),
                        revlistdir+prevdt.strftime('/revlist%Y%m%d.%H.csv'),
                        revlistdir+fnamedt.strftime('/revlist%Y%m%d.%H.csv'),
                        revlistdir+fnamedt2.strftime('/revlist%Y%m%d.%H.csv')]
        return revlistfnames

    def get_datetime(self):

        revlistfnames = self.get_revlist_fnames()
        dt = None
        done = False
        for revlistfname in revlistfnames:
            if os.path.exists(revlistfname) and not done:
                #print revlistfname
            #00533, 2014-300T18:51:09.582, 2014-300T20:23:56.187, -162.450, MARGINAL / Poor echo centering
                for line in reversed(list(open(revlistfname))):
                    if done:
                        continue
                    lineparts = line.split(',')
                    #print 'lp'+lineparts[0]+' rn'+self.RS_datatyperevnum+'rn'
                    # datatype is RS_S2B00877
                    if lineparts[0] in self.RS_datatyperevnum:
                        #print '    lp=rn '+lineparts[1]
                        try:
                            dt = datetime.strptime(lineparts[1].split('.')[0],' %Y-%jT%H:%M:%S')
                            log.debug('       dt set from revlist file data times')
                        except Exception,resp:
                            log.warning('       dt not set from revlist file, look at file format '+revlistfname+' '+str(resp))
                        done=True

        if not dt:
            log.info('setting default dt from filename (creation time, not data time)')
            dt = self.datetime
            extra = self.RS_datatyperevnum+'_filectime'
        else:
            extra = self.RS_datatyperevnum+'_datatime_c'+self.date
        return dt,extra

    # Return our standard filenaming convention, from parsing orig fname format
    def set_fields(self,df,wildcards=False,scifile_obj=None):
        # RS_S2B00563.20143021221
        # from utils.satname_info.RSCATSensorInfo:
        # <RS_datatyperevnum>.<date{%Y%j%H%M}>

        dt,extra = self.get_datetime()
        df.datetime = dt
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = self.sensorinfo.satname
        df.sensorname = self.sensorinfo.sensorname
        df.scifile_source = df.sensorname
        df.dataprovider = 'jplrscat' if df.dataprovider is df.get_fillvalue() else df.dataprovider
        df.resolution = '25p0km'
        # this is soltype - original HDF file has all solutions - primary and all ambiguities.
        # this must change in 
        df.channel = 'all'
        df.producttype = self.get_fillvalue()
        df.area = self.get_fillvalue()
        df.extra = extra
        # The original RSCAT file coming from JPL is an hdf file, there is no extension on the 
        # original filename
        df.ext = 'hdf'

        return df

class RSCATFileName(StandardDataFileName):

    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default), use that class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie RSCATFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        if self.rs == 'rs' and self.prodtype == 'l2b': 
            return True
        else:
            return False

    def get_revlist_fnames(self):
        fnamedt =  self.datetime
        nowdt = datetime.utcnow()
        prevdt = nowdt - timedelta(hours=1)
        fnamedt2 = fnamedt + timedelta(hours=1)
        for base_dir in self.sensorinfo.FName['base_dirs']:
            revlistdir = base_dir+'/rscat/revlists'
            #log.info('    Trying revlists in '+revlistdir)
            revlistfnames = [revlistdir+nowdt.strftime('/revlist%Y%m%d.%H.csv'),
                            revlistdir+prevdt.strftime('/revlist%Y%m%d.%H.csv'),
                            revlistdir+fnamedt.strftime('/revlist%Y%m%d.%H.csv'),
                            revlistdir+fnamedt2.strftime('/revlist%Y%m%d.%H.csv')]
        return revlistfnames

    def get_datetime(self,wildcards=False):

        extra = self.prodtype+'_'+self.vers+'_'+self.revnum
        if wildcards:
            return self.datetime,extra+'_*'
        revlistfnames = self.get_revlist_fnames()
        dt = None
        done = False
        for revlistfname in revlistfnames:
            #log.info('    Trying revlist file: '+revlistfname)
            if os.path.exists(revlistfname) and not done:
                #print revlistfname
            #00533, 2014-300T18:51:09.582, 2014-300T20:23:56.187, -162.450, MARGINAL / Poor echo centering
                for line in reversed(list(open(revlistfname))):
                    if done:
                        continue
                    lineparts = line.split(',')
                    #print 'lp'+lineparts[0]+' rn'+self.revnum+'rn'
                    # datatype is RS_S2B00877
                    if lineparts[0] in self.revnum:
                        #print '    lp=rn '+lineparts[1]
                        try:
                            dt = datetime.strptime(lineparts[1].split('.')[0],' %Y-%jT%H:%M:%S')
                            log.debug('       dt set from revlist file data times')
                        except Exception,resp:
                            log.warning('       dt not set from revlist file, look at file format '+revlistfname+' '+str(resp))
                        done=True

        if not dt:
            log.info('setting default dt from filename (creation time, not data time)')
            dt = self.datetime
            extra = extra+'_filectime'
        else:
            extra = extra+'_datatime_c'+self.date
        return dt,extra

    # Return our standard filenaming convention, from parsing orig fname format
    def set_fields(self,df,wildcards=False,scifile_obj=None):
        # RS_S2B00563.20143021221
        # from utils.satellite_info.RSCATSensorInfo:
        # <RS_datatyperevnum>.<date{%Y%j%H%M}>

        dt,extra = self.get_datetime(wildcards)
        df.datetime = dt
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = self.sensorinfo.satname
        df.sensorname = self.sensorinfo.sensorname
        df.scifile_source = df.sensorname
        df.dataprovider = 'jplrscat' if df.dataprovider is df.get_fillvalue() else df.dataprovider
        df.resolution = '12p5km'
        # this is soltype - original HDF file has all solutions - primary and all ambiguities.
        # this must change in 
        df.channel = 'all'
        df.producttype = self.get_fillvalue()
        df.area = self.get_fillvalue()
        df.extra = extra
        # The original RSCAT file coming from JPL is an hdf file, there is no extension on the 
        # original filename
        df.ext = self.ext

        return df


class RSCATKNMI25FileName(StandardDataFileName):

    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default), use that class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie RSCATFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        if self.rapid == 'rapid' and self.level == 'l2':
            return True
        else:
            return False

    # Return our standard filenaming convention, from parsing orig fname format
    def set_fields(self,df,wildcards=False,scifile_obj=None):
        # rapid_20160523_181659_iss____09461_2hr_o_250_1903_ovw_l2.nc
        # from utils.satellite_info.RSCATKNMI25SensorInfo:
        # <rapid>_<date{%Y%m%d}>_<time{%H%M%S}>_<sat>_<blank>_<blank>_<blank>_<rev>_<srv>_<type>_<resolution>_<vers>_<contents>_<level>'<RS_datatyperevnum>.<date{%Y%j%H%M}>

        df.date = self.date
        df.time = self.time
        df.datetime = self.datetime
        df.satname = self.sat
        #df.sensorname = self.sensorinfo.sensorname
        df.sensorname = 'rscat'
        df.scifile_source = df.sensorname
        df.dataprovider = 'KNMI'
        df.resolution = '25km'
        df.channel = self.get_fillvalue()
        df.producttype = self.get_fillvalue()
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext

        return df

class SeviriHRITFileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie SeviriHRITFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype seviri'
        #print self.satname.lower()
        #print self.sensorinfo.satname
        # self.satname is from filename, self.sensorinfo is current attempt at matching format
        # Need to make sure both filename and sensorinfo match
        # MSG1 is Meteosat-8, which is currently meteoIO
        # MSG3 is Meteosat-10, which used to be meteoEU
        # MSG4 is Meteosat-11, which is currently meteoEU
        if self.satname == 'MSG1__'  and self.sensorinfo.satname == 'meteoIO':
            return True
        elif (self.satname == 'MSG2' or self.satname == 'MSG3__' or self.satname == 'MSG4__') and self.sensorinfo.satname == 'meteoEU':
            return True
        else:
            return False


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        # self.satname is from filename, self.sensorinfo is current attempt at matching format
        # Need to make sure both filename and sensorinfo match
        # MSG1 is Meteosat-8, which is currently meteoIO
        # MSG3 is Meteosat-10, which used to be meteoEU
        # MSG4 is Meteosat-11, which is currently meteoEU

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        # H-000-MSG1__-MSG1_IODC___-WV_073___-000005___-201612201830-C_
        # H-000-MSG4__-MSG4________-HRV______-000001___-201811191100-C_
        # OrigFName3['nameformat'] = '<resolution>-<always000>-<satname>-<alwaysmsg1iodc>-<channel>-<slice>-<date{%Y%m%d%H%M}>-<compression>'
        if self.satname == 'MSG3__' or self.satname == 'MSG4__':
            df.satname = 'meteoEU'
        if self.satname == 'MSG1__':
            df.satname = 'meteoIO'
        df.sensorname = self.sensorinfo.sensorname
        df.scifile_source = df.sensorname
        df.resolution = self.resolution
        df.channel = self.channel.replace('_','')+'_'+self.slice.replace('_','')
        df.producttype = self.get_fillvalue()
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = 'hrit'
        # LAME add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df

class SeviriTDFFileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie SeviriTDFFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype seviri'
        #print self.satname.lower()
        #print self.sensorinfo.satname
        # self.satname is from filename, self.sensorinfo is current attempt at matching format
        if self.satname.lower() in self.sensorinfo.satname and self.ext == 'tdfx':
            return True
        else:
            return False


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        #RNSCA-RVIRS_npp_d20141205_t0012213_e0013467_b16083_c20141205020902820922_noaa_ops.h5
        # From utils.satellite_info.VIIRSSensorInfo:
        #<datatype>_<satname>_<date{d%Y%m%d}>_<time{t%H%M%S%f}>_<endtime>_<orbitnum>_<creationtime>_<dataoriginator>_<datalevel>'
        #print 'setting npp fields'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = self.sensorinfo.satname
        df.sensorname = self.sensorinfo.sensorname
        df.scifile_source = df.sensorname
        df.resolution = self.get_fillvalue()
        df.channel = self.get_fillvalue()
        df.producttype = self.get_fillvalue()
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext
        # LAME add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df

class TPWHE4FileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie TPWHE4FileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype seviri'
        #print self.satname.lower()
        #print self.sensorinfo.satname
        # self.satname is from filename, self.sensorinfo is current attempt at matching format
        if self.npr == 'NPR' and self.comp == 'COMP' and self.tpw == 'TPW':
            return True
        else:
            return False


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        #RNSCA-RVIRS_npp_d20141205_t0012213_e0013467_b16083_c20141205020902820922_noaa_ops.h5
        # From utils.satellite_info.VIIRSSensorInfo:
        #<datatype>_<satname>_<date{d%Y%m%d}>_<time{t%H%M%S%f}>_<endtime>_<orbitnum>_<creationtime>_<dataoriginator>_<datalevel>'
        #print 'setting npp fields'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = 'multi'
        df.sensorname = 'tpw_cira'
        df.scifile_source = df.sensorname
        df.resolution = self.get_fillvalue()
        df.channel = self.get_fillvalue()
        df.producttype = 'tpw'
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext
        # add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df

class TPWMIMICFileName(StandardDataFileName):
    def istype(self):
        ''' 
        istype method is called after successfully matching a filename
        format.  If istype returns True (default in StandardDataFileName), 
        use the current class.
        If istype returns false, continue checking additional filename
        formats.  Override istype method in subclasses (ie TPWMIMICFileName)
        if there are more than one data types with the same filename
        format (look at a field within the filename to determine which
        data type it actually is
        '''
        #print 'in istype seviri'
        #print self.satname.lower()
        #print self.sensorinfo.satname
        # self.satname is from filename, self.sensorinfo is current attempt at matching format
        if 'comp' in self.name and self.ext == 'nc':
            return True
        else:
            return False


    def set_fields(self,df,wildcards=False,scifile_obj=None):
        #RNSCA-RVIRS_npp_d20141205_t0012213_e0013467_b16083_c20141205020902820922_noaa_ops.h5
        # From utils.satellite_info.VIIRSSensorInfo:
        #<datatype>_<satname>_<date{d%Y%m%d}>_<time{t%H%M%S%f}>_<endtime>_<orbitnum>_<creationtime>_<dataoriginator>_<datalevel>'
        #print 'setting npp fields'

        df.datetime = self.datetime
        dt_strs = df.set_datetime_str() 
        for dt_field in dt_strs.keys():
            setattr(df,dt_field,dt_strs[dt_field])
        df.satname = 'multisat'
        df.sensorname = 'tpw_mimic'
        df.scifile_source = df.sensorname
        df.resolution = self.get_fillvalue()
        df.channel = self.get_fillvalue()
        df.producttype = 'tpwmimic'
        df.area = self.get_fillvalue()
        df.extra = self.get_fillvalue()
        df.ext = self.ext
        # add pid/timestamp to output directory from rdr conversion.. in case
        # the conversion happens more than once
        #print 'dp and prodtype: '+df.dataprovider+' '+df.producttype
        #print 'Adding pid and timestamp'
        df._add_property('pid')
        df._add_property('timestamp')

        return df
