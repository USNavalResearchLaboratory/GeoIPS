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

# Python Standard Libraries
import pdb
import shutil
import getpass
import sys
import os
import logging
from glob import glob
from datetime import datetime,timedelta
import filecmp


# Installed Libraries
if not os.getenv('GEOIPS_OPERATIONAL_USER'):
    from IPython import embed as shell
else:
    def shell():
        pass


# GeoIPS Libraries
import geoips.sectorfile
from geoips.pass_prediction.pass_prediction import pass_prediction
from geoips.pass_prediction.pass_prediction import is_concurrent_with
from ..satellite_info import SatSensorInfo,all_available_sensors,all_available_satellites
from .filename import FileName
from .exceptions import PathFormatError
from ..log_setup import interactive_log_setup, root_log_setup
from ..plugin_paths import paths as gpaths


log = interactive_log_setup(logging.getLogger(__name__))

# These are standard between all output filenames at the moment.  Could add additional if necessary for future filename specifications
stdfieldsep = '.'
stdfillvalue='x'
stdnoext = False

# These are standard between all output paths at the moment.  Could add additional if necessary for future path specifications
stdpathfieldsep = '-'
stdpathfillvalue = 'x'

# These are the standard file name formats for the FINAL output imagery
# They are used in initializing the ProductFileName subclasses at the end of productfilename.py
GeoIPSnameformat = '<date{%Y%m%d}>.<time{%H%M%S}>.<satname>.<sensorname>.<productname>.<sectorname>.<coverage>.<dataprovider>.<extra>'
# These are the standard path name formats for the FINAL output imagery
# They are used in initializing the ProductFileName subclasses at the end of productfilename.py
GeoIPSpathnameformat=os.path.join('<basedir>','<continent>-<country>-<area>',
                                  '<subarea>-<state>-<city>','<productname>',
                                  '<sensorname>','<resolution>')
GeoIPSTCpathnameformat=os.path.join('<basedir>','<continent>','<area>',
                                    '<subarea>','<productname>','<sensorname>',
                                    '<resolution>')
# These are the standard path name formats for the temporary granule imagery. 
# They are used in initializing the ProductFileName subclasses at the end of productfilename.py
# Note the extra subdirectory for optime. This allows easy merging of all granules in a single swath.
# Also note the extra subdirectory for ext. This allows different intermediate output types - 
#       including data (h5), imagery (png, jpg), etc.
GeoIPSTEMPpathnameformat=os.path.join('<basedir>',
                                      '<continent>-<country>-<area>',
                                      '<subarea>-<state>-<city>',
                                      '<productname>',
                                      '<sensorname>',
                                      '<ext>',
                                      '<resolution>',
                                      '<optime>')
# NOTE - merging files for overlays does not work with differing GeoIPSTEMP paths. For now make them all
# the same. Need to rethink this at some point, maybe? (what if some formats don't have the same fields...)
# this will not be a problem when we have a database (we won't rely on directory structure to list files, 
# we can query the database for them), but in the meantime, hopefully this will work.
#GeoIPSTEMPTCpathnameformat=os.path.join('<basedir>','<continent>','<area>',
                                        #'<subarea>','<productname>',
                                        #'<sensorname>','<ext>','<resolution>',
                                        #'<optime>')


atcffieldsep = '_'
# Note in sectorfile/dynamic.py parse_atcf, we are explicitly setting 
#    sector.name_info.continent = "tc"+str(tcyear)
#    sector.name_info.country = interp['wind_speed']
#    sector.name_info.area = interp['basin']
#    sector.name_info.subarea = interp['basin']+interp['stormnum']+str(tcyear)
# <tcyear>    sector.name_info.continent = "tc"+str(tcyear)
# <basin>     sector.name_info.subarea = interp['basin']
# <atcfid>    sector.name_info.state = interp['basin']+interp['stormnum']+str(tcyear)
# <intensity> sector.tc_info.wind_speed = interp['wind_speed']
# NOTE: extra field EXPECTED and NECESSARY for merging, etc. Not sure how to get around it without 
#       getting database working.
#ATCFnameformat = '<date{%Y%m%d%H%M}>_<atcfid>_<sensorname>_<productname>_<intensity>_<coverage>'
ATCFnameformat = '<date{%Y%m%d%H%M}>_<state>_<sensorname>_<satname>_<productname>_<intensity>_<coverage>_<extra>'
#ATCFpathnameformat='<basedir>','<tcyear>','<basin>','<atcfid>','<ext>','<productname>'
ATCFpathnameformat=os.path.join('<basedir>','<continent>','<subarea>',
                                '<state>','<ext>','<productname>','<satname>')

# JTWC requested filename format
Metoctiffnameformat = '<date{%Y%m%d}>.<time{%H%M%S}>.<sensorname>.<productname>.<sectorname>.<coverage>'
metoctiffpathnameformat=os.path.join('<basedir>','<continent>','<area>',
                                     '<subarea>','<dirproductname>')

# Uses GeoIPSnameformat
TCWebIRVispathnameformat=os.path.join('<basedir>','<continent>','<area>',
                                      '<subarea>','<dirproductname>',
                                      '<sensorname>','<resolution>')
# Uses GeoIPSnameformat
nexsatpathnameformat=os.path.join('<basedir>','<continent>-<country>-<area>',
                                  '<subarea>-<state>-<city>',
                                  '<dirproductname>','<dirsensorname>')

# Uses GeoIPSnameformat
pyrocb_pathfieldsep = '-'
pyrocbpathnameformat=os.path.join('<basedir>','<continent>-<country>-<area>',
                                  '<subarea>-<state>-<city>',
                                  '<dirproductname>','<sensorname>-<satname>')

# Uses GeoIPSnameformat
atmosriver_pathfieldsep = '-'
atmosriverpathnameformat=os.path.join('<basedir>',
                                      '<continent>-<country>-<area>',
                                      '<subarea>-<state>-<city>',
                                      '<dirproductname>',
                                      '<sensorname>-<satname>')

# Allow for different internal paths within GeoIPS.
# Josh wants internal paths to vary for TCs
GeoIPSProductFileNameClasses = ['GeoIPSProductFileName',
                            'GeoIPSATCFProductFileName',
                            'GeoIPSTCProductFileName',
                            ]

# These are all the possible types of External ProductFileNames
# The keys match up with the strings in sectorobj.destinations_dict.keys()
#   that is passed into fromobjects
# The values match up with the ProductFileName subclasses found at the 
#   end of productfilename.py
ExternalProductFileNameClasses = { 
                            'tc': 'TCWebIRVisProductFileName',
                            'atcf': 'ATCFProductFileName',
                            'metoctiff': 'MetoctiffProductFileName',
                            'public': 'NexsatProductFileName',
                            'pyrocb': 'PyroCBProductFileName',
                            'atmosriver': 'AtmosRiverProductFileName',
                            'private': 'SatmetocProductFileName'
                        }

allProductFileNameClasses = GeoIPSProductFileNameClasses+ExternalProductFileNameClasses.values()
        
# The keys are the GeoIPS versions of the product names.
# The values are the Legacy path name versions of the product names (directory names on nexsat/TC web).  
# The values get mapped to <dirproductname> in the formats specified above.
nexsat_product_dir_names  = {
                    'True-Color': 'true_color',
                     'Infrared': 'ir_images',
                     'Visible': 'vis_images',
                     'Night-Vis-IR': 'night_vis',
                     'Night-Visible': 'Night-Visible',
                     'Natural-Color': 'day_natural_color',
                     'Dust-Enhance': 'dust_enhance',
                     'Dust-Bluelight': 'dust_enhance',
                     'Binary-Cloud-Snow': 'cloud_snow',
                     'Multi-Cloud-Snow': 'high_low_cloud',
                    }
# The keys are the GeoIPS versions of the product names.
# The values are the Legacy path name versions of the product names (directory names on nexsat/TC web).  
# The values get mapped to <dirsensorname> in the formats specified above.
nexsat_sensor_dir_names = {
                        'gvar' : 'goes'
                    }
tcirvis_product_dir_names  = {
                     'Infrared': 'ir',
                     'Visible': 'vis',
                     'Vapor': 'vapor',
                     'metoctiff': 'atcf'
                    }
metoctiff_product_dir_names = {
                    'Infrared': 'atcf',
                    'Visible': 'atcf',
                    }
product_dir_names = { 'public' : nexsat_product_dir_names,
                      'private': nexsat_product_dir_names,
                      'tc': tcirvis_product_dir_names,
                      'metoctiff': metoctiff_product_dir_names,
                    }
sensor_dir_names = { 'public' : nexsat_sensor_dir_names }


lognameformat=GeoIPSnameformat+'.<prefix>.<script>.<pid>.<timestamp>'
logpathnameformat = os.path.join(gpaths['LOGDIR'],'<sensorname>','<prefix>',
                                 '<date{%Y%m%d}>','<sectorname>')

class ProductFileName(object):
    '''
    provide an interface to easily create and modify Product specific filenames.
    While FileName requires `path` and `nameformat`, ProductFileName can be called
    with no arguments, creating a `fillvalue` filled 'empty' filename in the default
    `nameformat`. the _propertyTest tests are NOT performed when field value is `fillvalue` 

        >>> pf = ProductFileName()
        >>> pf.name = 'x.x.x.x.x.x.x.x.x.ext'

    If ProductFileName() is called with one of 
        nameformat
        fieldsep
        fillvalue
        pathnameformat      
        pathfieldsep
        pathfillvalue
    it must be called with ALL. This will override trying to use the default 
    file name format for ProductFileName
    '''
    def __new__(typ, path=None,
            nameformat=None,
            fieldsep=None,
            fillvalue=None,
            pathnameformat=None,
            pathfieldsep=None,
            pathfillvalue=None,
            noextension=False):

        # If path not included, create empty path from 
        # appropriate formats
        if not path:
            # If nameformat is not included, use defaults for 
            # ProductFileName
            if not nameformat:
                #print 'nameformat not passed'
                currfieldsep = stdfieldsep
                currfillvalue = stdfillvalue
                currnameformat = GeoIPSnameformat
                currpathnameformat = GeoIPSpathnameformat
                currpathfieldsep = stdpathfieldsep
                currpathfillvalue = stdpathfillvalue
                currnoext = stdnoext
            # If nameformat is included (and all associated parameters!), 
            # but path is not, use passed formats to create empty path, 
            # and create empty StandardDataFileName object
            else:
                #print 'nameformat passed'
                currnameformat = nameformat
                currfieldsep = fieldsep
                currfillvalue = fillvalue
                currpathnameformat = pathnameformat
                currpathfieldsep = pathfieldsep
                currpathfillvalue = pathfillvalue
                currnoext = noextension

            stdpath = typ.create_empty_dirname(currpathnameformat,currpathfieldsep,currpathfillvalue)
            stdfn = typ.create_empty_basename(currnameformat,currfieldsep,currfillvalue)

            #print stdpath
            #print GeoIPSpathnameformat
            #print currpathnameformat
            #print currfillvalue
            #print 'full empty stdpath from ProductFileName(): '+stdpath+'/'+stdfn
            obj = GeoIPSProductFileName(os.path.join(stdpath,stdfn),
                    nameformat=currnameformat,
                    fieldsep=currfieldsep,
                    fillvalue=currfillvalue,
                    pathnameformat=currpathnameformat,
                    pathfieldsep=currpathfieldsep,
                    pathfillvalue=currpathfillvalue,
                    noextension=currnoext )
            return obj

# This needs rolled into not nameformat stuff
#        if not path and nameformat:
#            stdpath = (fieldsep).join([fillvalue for field in nameformat.split(fieldsep)])+'.ext'
#            obj = GeoIPSProductFileName(stdpath,nameformat,fieldsep,fillvalue,
#                    pathnameformat,pathfieldsep,pathfillvalue,stdnoext)
#            return obj

        # If path and nameformat are included, use passed format and passed path
        # to create StandardDataFileName object
        if path and nameformat:
            obj = GeoIPSProductFileName(path,nameformat,fieldsep,fillvalue,
                    pathnameformat,pathfieldsep,pathfillvalue,noextension
                    )
            obj.sensorinfo = None
            return obj

        # If path is designated, but not nameformat, use default nameformat
        if path and not nameformat:
            #print path
            #print GeoIPSnameformat
            #print GeoIPSpathnameformat

            # If standard product filename didn't work, try the web versions
            #print 'path and not nameformat'
            #pdb.set_trace()
            retobj = None
            #print allProductFileNameClasses
            for pfnclsname in allProductFileNameClasses:
                try:
                    #if 'nexsat_www' in path:
                        #shell()
                    #print pfnclsname
                    pfcls = getattr(sys.modules[__name__],pfnclsname)
                    #print 'try pfcls: '+str(pfcls)
                    pfobj = pfcls(path,pfcls.nameformat,pfcls.fieldsep,pfcls.fillvalue,
                        pfcls.pathnameformat,pfcls.pathfieldsep,pfcls.pathfillvalue,pfcls.noext
                        )
                    #print 'try pfobj.istype: '+str(pfobj.istype())
                    if pfobj.istype():
                        retobj = pfobj
                    else:
                        if hasattr(pfcls,'geoipstemppathnameformat'):
                            try:
                                #print '    geoipstemppathnameformat: '+pfcls.geoipstemppathnameformat
                                #print '    nameformat: '+pfcls.nameformat
                                #print '    path: '+path
                                pfobj = pfcls(path,
                                            pfcls.nameformat,
                                            pfcls.fieldsep,
                                            pfcls.fillvalue,
                                            pfcls.geoipstemppathnameformat,
                                            pfcls.pathfieldsep,
                                            pfcls.pathfillvalue,
                                            pfcls.noext
                                    )
                                #print '    gt pfobj.istype: '+str(pfobj.istype())
                                if pfobj.istype():
                                    retobj = pfobj
                            except PathFormatError:
                                continue
                except PathFormatError:
                    # Put granules in subdirectories of overpass time.
                    # Only try this is geoipstemppathnameformat is defined.
                    #print '    except pfcls: '+str(pfcls)
                    if hasattr(pfcls,'geoipstemppathnameformat'):
                        try:
                            #print '        geoipstemppathnameformat: '+pfcls.geoipstemppathnameformat
                            #print '        nameformat: '+pfcls.nameformat
                            pfobj = pfcls(path,
                                        pfcls.nameformat,
                                        pfcls.fieldsep,
                                        pfcls.fillvalue,
                                        pfcls.geoipstemppathnameformat,
                                        pfcls.pathfieldsep,
                                        pfcls.pathfillvalue,
                                        pfcls.noext
                                
                                )
                            #print '        gt pfobj.istype: '+str(pfobj.istype())
                            if pfobj.istype():
                                retobj = pfobj
                        except PathFormatError:
                            continue
                    continue
            #print 'retobj: '+str(retobj)
            if retobj:
                return retobj
        raise PathFormatError('Did not match any filename formats! Fail! '+str(path))

    @staticmethod
    def nearest_file(sat,sensor,sector,productname,start_dt,end_dt,maxtimediff=timedelta(minutes=120),matchall = False,intermediate_data=False):
        '''Return the file closest to time nearest_dt, of the given sat,sensor,sector,product'''
        sdt = start_dt - maxtimediff
        edt = end_dt + maxtimediff
        nearest_dt = start_dt + (end_dt - start_dt)/2
        files=[]
        for n in range((edt-sdt).days*24 + (edt-sdt).seconds/3600): 
            pfn = ProductFileName.from_satsensor(sat,sensor,
                        wildcards=True,
                        nearest_dt=sdt+timedelta(hours=n),
                        sector=sector,  
                        productname=productname,
                        intermediate_data=intermediate_data,
                        )
            #print pfn.name
            files+=glob(pfn.name)
        if matchall:
            return [ProductFileName(file) for file in set(files)]
        log.info('Searching for '+pfn.name)

        best_time = None
        best_covg = None
        #print files
        for mfile in set(files):

            pfn = ProductFileName(mfile)
            best_covg,best_time = pfn.get_best_match(best_covg,best_time,nearest_dt)

        if best_time and best_time.coverage_to_float() == best_covg.coverage_to_float():
            return best_time
        else:
            return best_covg

    @staticmethod
    def list_range_of_files(sat,sensor,start_datetime,end_datetime,
                            sector,product,
                            datetime_wildcards = {'%H':'*%H','%M':'*','%S':'*'},
                            data_provider = '*',
                            coverage='*',
                            extra='*',
                            intensity='*',
                            ext = '*',):
        allfiles = []
        from utils.path.filename import daterange
        for curr_dt in daterange(start_datetime,end_datetime,hours=True):
            #print curr_dt
            pfn = ProductFileName.from_satsensor(sat,sensor,
                                        wildcards=True,
                                        sector = sector,
                                        nearest_dt = curr_dt,
                                        productname = product.name,
                                        datetime_wildcards = datetime_wildcards,
                                        final = True)
            pfn.dataprovidder = data_provider
            pfn.coverage = coverage
            pfn.extra = extra
            pfn.intensity = intensity
            pfn.ext = ext
            #print pfn
            if os.path.exists(os.path.dirname(pfn.name)) or '*' in os.path.dirname(pfn.name):
                #print 'globbing '+os.path.dirname(pfn.name)
                allfiles += glob(pfn.name) 
                
            if curr_dt == start_datetime:
                log.info('Trying '+pfn.name)
                log.info('      from '+str(start_datetime)+' to '+str(end_datetime))


        return list(set(allfiles))
                            
            
    @staticmethod
    def from_satsensor(sat,sensor,
                        path=None,
                        wildcards=False,
                        datetime_wildcards={'%H':'*','%M':'*','%S':'*'},
                        nearest_dt=None,
                        sector=None,
                        productname=None,
                        final=False,
                        intermediate_data=False):
        '''Return appropriate FileName subclass object using passed sat/sensor'''

        #print 'opening ProductFileName from_satsensor'
        print_dtstrs = "      "

        if wildcards:
            #print 'passing wildcards for fillvalues'
            fnfillvalue = '*'
            pathfillvalue = '*'
        else:
            #print 'using standard fillvalues'
            fnfillvalue = stdfillvalue
            pathfillvalue = stdpathfillvalue

        # Default to GeoIPS ProductFileName. Works for geoipsfinal or geoipstemp
        pfcls = getattr(sys.modules[__name__],'GeoIPSProductFileName')
        # Still GeoIPS internal naming - just allowing for special case where
        # products specified as 'tc' follow a different path/name convention
        # than others within GeoIPS temp/final.
        if sector.tc_on:
            pfcls = getattr(sys.modules[__name__],'GeoIPSTCProductFileName')
        elif sector.atcf_on:
            pfcls = getattr(sys.modules[__name__],'GeoIPSATCFProductFileName')

        pathnameformat = pfcls.geoipstemppathnameformat
        if final:
            pathnameformat = pfcls.pathnameformat

        # Use the approrpiate class
        pfn = ProductFileName(
            path=None,
            nameformat=pfcls.nameformat,
            fieldsep=pfcls.fieldsep,
            fillvalue=fnfillvalue,
            pathnameformat=pathnameformat,
            pathfieldsep=pfcls.pathfieldsep,
            pathfillvalue=pathfillvalue,
            noextension=pfcls.noext)

        pfn.satname = sat
        pfn.sensorname = sensor
        # Go through all the datetime_fields, looking for the ones that
        #   define datetime_wildcards fields, and replace with wildcarded values.
        dt_strs = pfn.set_datetime_str(nearest_dt,datetime_wildcards=datetime_wildcards,datetime_fields=pfn.datetime_fields) 
        for dt_field in pfn.datetime_fields.keys():
            pfn.datetime = nearest_dt
            setattr(pfn,dt_field,dt_strs[dt_field])
            print_dtstrs += ' '+str(dt_strs[dt_field])
        pfn.basedir = gpaths['GEOIPSTEMP']
        if final:
            pfn.basedir = gpaths['GEOIPSFINAL']
        # MLS 20160613 THIS IS WHERE WE NEED TO MAKE IT LOOK MORE LIKE datafilename.py
        #       allow for different fields
        if sector:
            pfn.continent = sector.name_info.name_dict['continent']
            pfn.country = sector.name_info.name_dict['country']
            pfn.area = sector.name_info.name_dict['area']
            pfn.subarea = sector.name_info.name_dict['subarea']
            pfn.state = sector.name_info.name_dict['state']
            pfn.city = sector.name_info.name_dict['city']
            # MLS need to clean this up to allow different naming for different types
            if hasattr(sector,'tc_info') and hasattr(sector.tc_info,'wind_speed'):
                if not wildcards:
                    pfn.intensity = sector.tc_info.wind_speed
                else:
                    pfn.intensity = '*'
        if productname: 
            # MLS Can't have _ if _ is field separator......
            pfn.productname = productname
            pfn.productname = productname
        if intermediate_data:
            pfn.ext = pfcls.data_ext
        else:
            pfcls.ext
        pfn.resolution = sector.area_info.display_resolution.replace('.','p')
        pfn.optime = 'fullcomposites'
        #log.info('Trying '+pfn.name)
        #log.info(print_dtstrs)

        return pfn

    @staticmethod
    def create_empty_basename(nameformat,fieldsep,fillvalue):
        #print stdfn
        return (fieldsep.join([fillvalue for field in (nameformat.split(fieldsep))]))+'.ext'


    @staticmethod
    def create_empty_dirname(pathnameformat,pathfieldsep,pathfillvalue):
        stdpathparts = []
        for pathpart in pathnameformat.split(os.path.sep):
            pathpart = pathpart.strip()
            if not pathpart:
                stdpathpart = ''
            else:
                #print '    pathpart: '+str(pathpart)
                stdpathpart = (pathfieldsep.join([pathfillvalue for field in (pathpart.split(pathfieldsep))]))
                #print '    stdpathpart: '+str(pathpart)
            stdpathparts += [stdpathpart]
        return os.path.sep.join(stdpathparts)

    # geoipsfinal_product and external_product can not both be set
    # We are only returning one filename...
    @staticmethod
    def fromobjects(data_file=None,
                    sectorobj=None,
                    productobj=None,
                    geoimgobj=None,
                    geoipsfinal_product=False,
                    data_output=False,
                    text_output=False,
                    external_product=None,
                    merged='GRANULE',
                    imgkey=None,
                    ):
        # If both geoipsfinal_product and external_product are defined, fail!
        # We should only return one filename, so this would be ambiguous!
        if geoipsfinal_product and external_product:
            raise('geoipsfinal_product and external_product can not both be set - one or the other please!')
        # If we are requesting an external product, and we don't have a class defined for it,
        # return None
        if external_product and external_product not in ExternalProductFileNameClasses.keys():
            #print external_product+' not in ExternalProductFileNameClasses.keys() '+str(ExternalProductFileNameClasses.keys())
            return None
        #print pf.name
        #print data_dict
        #print sectorobj
        #print productobj

        # Initialize this to None, so we return None below if it never manages to get set (instead of just failing...)
        curr_basedir = None

        # Default to GeoIPS ProductFileName. Works for geoipsfinal or geoipstemp
        pfcls = getattr(sys.modules[__name__],'GeoIPSProductFileName')
        # Still GeoIPS internal naming - just allowing for special case where
        # products specified as 'tc' follow a different path/name convention
        # than others within GeoIPS temp/final.
        if sectorobj.tc_on:
            pfcls = getattr(sys.modules[__name__],'GeoIPSTCProductFileName')
        elif sectorobj.atcf_on:
            pfcls = getattr(sys.modules[__name__],'GeoIPSATCFProductFileName')
        if productobj:
            dirprodname = productobj.name
        if data_file:
            dirsensorname = data_file.source_name_product
        linkdirs = []
        if geoipsfinal_product:
            curr_basedir = gpaths['GEOIPSFINAL']
        elif external_product:
            #print 'Trying to set up external_product'
            external_class = ExternalProductFileNameClasses[external_product]
            ## Maybe need this in the future for something ?
            ## dopublic = data_file.produce_public
            #dopublic = True
            testonly = False

            # Aha!  Will not produce external imagery if productobj.testonly 
            # or sectorobj.testonly is True!
            if (hasattr(productobj,'testonly') and productobj.testonly) \
                or (hasattr(sectorobj,'testonly') and sectorobj.testonly):
                log.info('    testonly set to true on productobj or on sectorobj, so not producing external product '+str(external_product))
                testonly = True

            if not testonly:
                # This takes the value of string external_class and 
                # turns it into the actual class.  So pfcls is actually a 
                # class.
                pfcls = getattr(sys.modules[__name__],external_class)
                curr_basedir = pfcls.basedir
                # Only set dirprodname to alternative if it is defined in the dictionary above.
                if productobj and external_product in product_dir_names.keys() and productobj.name in product_dir_names[external_product].keys():
                    dirprodname = product_dir_names[external_product][productobj.name]
                if data_file and external_product in sensor_dir_names.keys() and data_file.source_name_product in sensor_dir_names[external_product].keys():
                    dirsensorname = sensor_dir_names[external_product][data_file.source_name_product]

                # Returns empty list if property doesn't exist.
                # But fails if property is not defined at all (don't need to explicitly add atcf_link property
                # to sectorfile/xml.py, so didn't. Don't fail if it is not there.)
                if hasattr(sectorobj,external_product+'_link'):
                    linkdirs.append(getattr(sectorobj,external_product+'_link'))

        else:
            curr_basedir = gpaths['GEOIPSTEMP']
        if not curr_basedir:
            return None

        # GRANULE files go in dynamic subdirectory within GEOIPSTEMP path of 
        #     the OVERPASS TIME that particular granule falls within.
        # FULLCOMPOSITE files go in static subdirectory within GEOIPSTEMP 
        #     path of 'fullcomposite'
        # SWATH files just go in the top level TEMP directory (so they are all 
        #     in the same place for merging.
        # FINAL files never go in subdirectories, so only use geoipstemppathnameformat 
        #     if not geoipsfinal_product
        # use geoipstemppathnameformat for the cases that have an extra
        # directory level.
        #if merged == 'GRANULE' or merged == 'SWATH' and hasattr(pfcls,'geoipstemppathnameformat'):
        if not geoipsfinal_product and (merged == 'GRANULE' or merged == 'FULLCOMPOSITE' or merged == 'SWATH') and hasattr(pfcls,'geoipstemppathnameformat'):
            pathnameformat = pfcls.geoipstemppathnameformat
        else:
            pathnameformat = pfcls.pathnameformat

        pf = ProductFileName(
            nameformat=pfcls.nameformat,
            fieldsep=pfcls.fieldsep,
            fillvalue=pfcls.fillvalue,
            pathnameformat=pathnameformat,
            pathfieldsep=pfcls.pathfieldsep,
            pathfillvalue=pfcls.pathfillvalue,
            noextension=pfcls.noext)
        if hasattr(pf,'dirproductname'):
            pf.dirproductname = dirprodname
        if hasattr(pf,'dirsensorname'):
            pf.dirsensorname = dirsensorname
        pf.basedir = curr_basedir
        if data_output:
            pf.ext = pfcls.data_ext
        elif text_output:
            pf.ext = pfcls.text_ext
        else:
            pf.ext = pfcls.ext
        pf.linkdirs = linkdirs
        
        if hasattr(pf,'extra') and merged and not geoipsfinal_product:
            if pf.extra and pf.extra != pf.get_fillvalue():
                pf.extra += merged
            else:
                pf.extra = merged

        dp = None
        if not sectorobj:
            pf.sectorname = pf.get_fillvalue()
            pf.continent = pf.get_fillvalue()
            pf.country = pf.get_fillvalue()
            pf.area = pf.get_fillvalue()
            pf.subarea = pf.get_fillvalue()
            pf.state = pf.get_fillvalue()
            pf.city = pf.get_fillvalue()
            pf.resolution = pf.get_fillvalue()
            pf.pixel_width = None
            pf.pixel_height = None
            #print 'sector fill: '+pf.continent
        else:
            # MLS 20160613 THIS IS WHERE WE NEED TO MAKE IT LOOK MORE LIKE datafilename.py
            #       allow for different fields
            pf.sectorname = sectorobj.sector_name_product
            pf.continent = sectorobj.name_info.continent or pf.get_fillvalue()
            pf.country = sectorobj.name_info.country or pf.get_fillvalue()
            pf.area = sectorobj.name_info.area or pf.get_fillvalue()
            pf.subarea = sectorobj.name_info.subarea or pf.get_fillvalue()
            pf.state = sectorobj.name_info.state or pf.get_fillvalue()
            pf.city = sectorobj.name_info.city or pf.get_fillvalue()
            if hasattr(sectorobj,'tc_info') and hasattr(sectorobj.tc_info,'wind_speed'):
                pf.intensity = sectorobj.tc_info.wind_speed
            pf.pixel_width = sectorobj.area_info.proj4_pixel_width
            pf.pixel_height = sectorobj.area_info.proj4_pixel_height
            pf.resolution = sectorobj.area_info.display_resolution.replace('.','p')

            #print ' sector resolution: '+pf.resolution
            #print 'sector exists: '+pf.continent
            ###MLS 20160608 - dynamic tc times change slightly for different data times, and can screw up merging. 
            ### I'm guessing it's going to screw something up to take it out
            ### it's going to have to be tweaked for 
            ### intermediate data files anyway (putting dynamic time in temporary data files doesn't make sense 
            ### anyway, because it is just data, and the center hasn't been determined yet.
            ###if sectorobj.isdynamic:
            ###    pf.sectorname += '_'+str(sectorobj.dynamic_datetime.strftime('%m%d%H%M'))
            #if productobj:
            #    try:
            #        if productobj.product_args.best_possible_pixel_width > sectorobj.area_info.pixel_width:
            #            pf.resolution = str(productobj.product_args.best_possible_pixel_width)+'km'
            #            print(' product resolution: '+pf.resolution)
            #    except AttributeError:
            #        print('best_possible_pixel_width/height not defined for product in ProductFileName, using sector pixel_width/height')
        if productobj is None:
            pf.productname = pf.get_fillvalue()
            #print 'product fill: '+pf.productname
        else:
            if imgkey:
                pf.productname = productobj.name+imgkey
            else:
                pf.productname = productobj.name
                
            #print 'product exists: '+pf.productname
        if data_file:
            # Default to using geoimgobj - in case of merged granules
            if not geoimgobj:
                if data_file.start_datetime != data_file.end_datetime:
                    pf.end_time = data_file.end_datetime.strftime('%H%M%S')
                for dt_field in pf.datetime_fields.keys():
                    setattr(pf,dt_field,data_file.start_datetime.strftime(pf.datetime_fields[dt_field]))
                # Make this work for arbitrary datetime fields.  Failed on ATCF, which just
                #   has pf.date
                #pf.date = data_file.start_datetime.strftime('%Y%m%d')
                #pf.time = data_file.start_datetime.strftime('%H%M%S')
            pf.satname = data_file.platform_name_product
            pf.sensorname = data_file.source_name_product
            dp  = data_file.dataprovider
            #print 'data exists: '+pf.satname
            if dp and dp != None:
                pf.dataprovider = dp.replace('_','')
                pf.dataprovider = pf.dataprovider.replace('.','')
        if pf.resolution:
            pf.resolution = pf.resolution.replace('.','p')
            if hasattr(pf,'extra'):
                if pf.extra and pf.extra != pf.get_fillvalue():
                    pf.extra += 'res'+pf.resolution
                else:
                    pf.extra = 'res'+pf.resolution
        if geoimgobj is None:
            pf.coverage = pf.get_fillvalue()
        else:
            # uses covg in filename to find coverages to only display 
            # latest on web. Add covg to coverage field for easier parsing.
            # MLS 20150622
            #print 'SHELL productfilename merging'
            #shell()
            if imgkey:
                pf.coverage = 'covg'+str(round(geoimgobj.coverage(imgkey),1)).replace('.','p')
            else:
                pf.coverage = 'covg'+str(round(geoimgobj.coverage(),1)).replace('.','p')
            #  MLS DEFAULT TO GEOIMGOBJ START_DATETIME!!
            pf.datetime = geoimgobj.start_datetime
            #pdb.set_trace()
            data_start_datetime = geoimgobj.start_datetime
            data_end_datetime = geoimgobj.end_datetime
            # Default to using geoimgobj for times - in case of merged granules
            if geoimgobj.start_datetime != geoimgobj.end_datetime:
                pf.end_time = geoimgobj.end_datetime.strftime('%H%M%S')
            for dt_field in pf.datetime_fields.keys():
                setattr(pf,dt_field,geoimgobj.start_datetime.strftime(pf.datetime_fields[dt_field]))
            # Make this work for arbitrary datetime fields.  Failed on ATCF, which just
            #   has pf.date
            #pf.time = geoimgobj.start_datetime.strftime(pf.datetime_fields['time'])
            #pf.date = geoimgobj.start_datetime.strftime(pf.datetime_fields['date'])
            # Default to filename_datetime (so if internal data times don't match, we have 
            # something common to go off of). If we don't have filename_datetime, just 
            # use geoimgobj start_datetime. This is important for Himawari-8 because there 
            # are 16 different channel data files for each acquisition time, and they all 
            # have slightly different start times, but we want them all in the same image.
            try:
                pf.optime = geoimgobj.datafile.filename_datetime.strftime('%Y%m%d.%H%M')
            except:
                pf.optime = geoimgobj.start_datetime.strftime('%Y%m%d.%H%M')
            #print 'initial pf.optime: '+str(pf.optime)
            # Find overpass for current image.
            si = SatSensorInfo(pf.satname,pf.sensorname)
            # Should be /4, to get half orbital period. Half orbital period 
            # will cover a single swath (full orbital period covers ascending 
            # and descending swaths on either side of globe)
            if si.orbital_period is not None:
                # Note /4 does not work very well for ?Arctic? sectors (or big sectors ?)
                # /3 works, but not sure if that would cause 
                # problems in general, so not changing it until I need to, and I have time
                # to fully test. I think big sectors. Failed for Arctic, and BigDateLineEq
                # This might be a problem operationally...
                op_test_start_datetime = pf.datetime - timedelta(minutes=si.orbital_period/60/4)
                op_test_end_datetime = pf.datetime + timedelta(minutes=si.orbital_period/60/4)
                if data_end_datetime > op_test_end_datetime:
                    op_test_end_datetime = data_end_datetime
                if data_start_datetime < op_test_start_datetime:
                    op_test_start_datetime = data_start_datetime
            sector_file = geoimgobj.sectorfile
            if merged == 'GRANULE' and si.orbital_period is not None:
                # leave optime as default for geostationary satellites

                # for leo, GRANULE and FULLCOMPOSITE images use geoipstemppathnameformat, which 
                # includes field for optime.  For granule files, this is the final 
                # directory level in the GEOIPSTEMP path that refers to the overpass 
                # time, so all the granules will be in a single directory. This 
                # makes merging faster, since there are fewer files per directory.
                if si.orbital_period is not None:
                    #pdb.set_trace()
                    # Note if this fails, it might be because the op_test_start_datetime and op_test_end_datetime
                    # do not provide a wide enough range.  See note above, where they are set.
                    opasses = pass_prediction([pf.satname],[pf.sensorname],sector_file,
                            [sectorobj.name.lower()],op_test_start_datetime,op_test_end_datetime,single=True,both=False,
                            force=True,quiet=True)
                    if opasses:
                        for op in opasses:
                            #print 'op basedt: '+op.basedt.strftime('%Y%m%d.%H%M')
                            if is_concurrent_with(op.startdt,data_start_datetime,op.enddt,data_end_datetime):
                                #print '    setting pf.optime'
                                pf.optime = op.basedt.strftime('%Y%m%d.%H%M')
                    else:
                        # If we don't have an overpass time and we should, put 
                        # everything in granules directory.
                        log.warning('NOTE: no opasses defined, putting all granules in same dir')
                        pf.optime = 'granules'
            if merged == 'SWATH' and si.orbital_period is not None:
                # leave pf.datetime/date/time as default for geostationary
                
                # for leo SWATH images, we want to set the actual date/time in the 
                # filename to the overpass time of that swath.  This way it 
                # doesn't change as the swath fills out, and we can more easily 
                # delete old files (they will all be named the same, with 
                # different coverages)
                if si.orbital_period is not None:
                    opasses = pass_prediction([pf.satname],[pf.sensorname],sector_file,
                            [sectorobj.name.lower()],op_test_start_datetime,op_test_end_datetime,single=True,both=False,
                            force=True,quiet=True)
                    if opasses:
                        pf.datetime = opasses[0].basedt
                        for dt_field in pf.datetime_fields.keys():
                            #print 'dt_field: '+str(dt_field)
                            setattr(pf,dt_field,opasses[0].basedt.strftime(pf.datetime_fields[dt_field]))
                    else:
                        # If we don't have an overpass time and we should, put 
                        # everything in granules directory.
                        pf.optime = 'granules'
                    # Make this work for arbitrary datetime fields.  Failed on ATCF, which just
                    #   has pf.date
                    #pf.date = opasses[0].basedt.strftime('%Y%m%d')
                    #pf.time = opasses[0].basedt.strftime('%H%M%S')
            if merged == 'FULLCOMPOSITE':
                # for FULLCOMPOSITE images, we just want them in their own 
                # subdirectory, so they are not filling up the directory 
                # with all the SWATH files in it that we are trying to merge 
                # together - speeds up merges. Reuse the optime attribute to 
                # create this subdirectory..
                pf.optime = 'fullcomposites'
            if merged == 'SWATH':
                pf.optime = 'swathcomposites'
        #print('extra: '+extra)
        return pf




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




class GeoIPSProductFileName(FileName):
    '''
    Standard Product filenames, this can be subclassed to provide descriptions
    of non-standard (old style TC, etc) filenames
    '''

    ext='png'
    data_ext = 'h5'
    nameformat = GeoIPSnameformat
    fieldsep = stdfieldsep
    fillvalue=stdfillvalue
    noext = stdnoext
    pathnameformat=GeoIPSpathnameformat
    geoipstemppathnameformat=GeoIPSTEMPpathnameformat
    pathfieldsep = stdpathfieldsep
    pathfillvalue = stdpathfillvalue

    def processing_set(self):
        if 'PROCESSING' in self.extra:
            #print 'PROCESSING is SET!'
            return True
        else:
            #print 'PROCESSING is NOT SET!'
            return False

    def coverage_to_float(self):
        return float(self.coverage.replace('p','.').replace('covg',''))

    def get_best_match(self,best_covg,best_time,nearest_dt):
        if not best_covg:
            best_covg = self
        if not best_time:
            best_time = self
        log.info('    Checking file: '+self.name+' current: ' +
                 str(abs(self.datetime-nearest_dt))+' best: ' +
                 str(abs(best_time.datetime-nearest_dt)))
        if self.coverage_to_float() > best_covg.coverage_to_float():
            #print 'new coverage better: '+str(self.coverage_to_float())
            best_covg = self
        if self.datetime == best_time.datetime and self.coverage_to_float() > best_time.coverage_to_float():
            #print 'new time better, better coverage: '+str(self.coverage_to_float())
            best_time = self
        elif abs(self.datetime - nearest_dt) < abs(best_time.datetime - nearest_dt):
            #print 'new time better: '+str(self.coverage_to_float())
            best_time = self
        return best_covg,best_time
        


    def set_processing(self):
        if self.extra == self.get_fillvalue():
            self.extra = 'PROCESSING'
        else:
            self.extra += 'PROCESSING'

    def move_to_final_filename(self):
        #print self.extra
        if self.extra == 'PROCESSING':
            fromname = self.name
            self.extra = self.get_fillvalue()
            toname = self.name
            #print 'PROCESSING in extra, move '+fromname+' to '+toname
            try:
                shutil.move(fromname,toname)
            except IOError,resp:
                log.error(str(resp)+' Someone must have already moved it for us ?')
                return False
            return True
        elif 'PROCESSING' in self.extra:
            fromname = self.name
            self.extra = self.extra.replace('PROCESSING','')
            toname = self.name
            #print 'PROCESSING in extra, move '+fromname+' to '+toname
            try:
                shutil.move(fromname,toname)
            except IOError,resp:
                log.error(str(resp)+' Someone must have already moved it for us ?')
                return False
            return True
        else:
            #print 'NO PROCESSING in extra, not moving'
            return False


    def istype(self):
        if gpaths['GEOIPSFINAL'] in self.basedir \
            or gpaths['GEOIPSTEMP'] in self.basedir \
            or str(os.getenv('ARCHDATWWW')) in self.basedir:
            allsats = all_available_satellites()
            allsens = all_available_sensors()
            #print allsats
            #print allsens
            #print self.sensorname
            #print self.satname
            #print self.resolution
            if 'km' in self.resolution and \
                self.sensorname in allsens \
                and self.satname in allsats:
                return True
        return False

    def open_new(self,fnamestr=None):
        if fnamestr:
            return ProductFileName(fnamestr)
        else:
            return ProductFileName()

    # MLS 20160419 should create_standard use lognameformat ?   
    def create_standard(self,geoips=True):
        pf = ProductFileName(path=None,
                nameformat=lognameformat,
                fieldsep=stdfieldsep,
                fillvalue=stdfillvalue,
                pathnameformat=logpathnameformat,
                pathfieldsep=stdpathfieldsep,
                pathfillvalue=stdpathfillvalue)
        #print 'StandardDataFileName create_logfile after DataFileName '+str(pf)
        pf = self.set_fields(pf)
        pf.ext = 'log'
        if geoips:
            pf.prefix = 'BP'
        else:
            pf.prefix = 'PP'
        pf.qsubname = pf.prefix+pf.sensorname+'_'+pf.dataprovider
        pf.qsubclassifier = pf.prefix+pf.sensorname
        return pf

    def create_logfile(self,geoips=True):
        pf = ProductFileName(path=None,
                nameformat=lognameformat,
                fieldsep=stdfieldsep,
                fillvalue=stdfillvalue,
                pathnameformat=logpathnameformat,
                pathfieldsep=stdpathfieldsep,
                pathfillvalue=stdpathfillvalue)
        #print 'StandardDataFileName create_logfile after DataFileName '+str(pf)
        pf = self.set_fields(pf)
        pf.ext = 'log'
        if geoips:
            if pf.sectorname == stdfillvalue:
                pf.prefix = 'GW'
            else:
                pf.prefix = 'GP'
        else:
            pf.prefix = 'PW'
        if pf.datetime:
            pf.qsubname = pf.prefix+pf.sensorname+pf.datetime.strftime('%d%H%M')
            pf.qsubclassifier = pf.prefix+pf.sensorname
        else:
            pf.qsubname = pf.prefix+pf.sensorname
            pf.qsubclassifier = pf.prefix+pf.sensorname
        if pf.sectorname != stdfillvalue:
            pf.qsubname += pf.sectorname
        if pf.dataprovider != stdfillvalue:
            pf.qsubname += '_'+pf.dataprovider
        pf._add_property('pid')
        setattr(pf,'pid','pid'+str(os.getpid()))
        pf._add_property('timestamp')
        setattr(pf,'timestamp','ts'+datetime.utcnow().strftime('%d%H%M%S'))
        return pf

    def create_scratchfile(self,geoips=True):
        
        #print 'StandardDataFileName create_logfile'
        if hasattr(self,'sensorinfo') and self.sensorinfo:
            si = self.sensorinfo
        else:
            si = SatSensorInfo()
        #print si.ScratchFName
        df = ProductFileName(path=None,
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
        df = self.set_fields(df)
        df._add_property('pid')
        setattr(df,'pid','pid'+str(os.getpid()))
        df._add_property('timestamp')
        setattr(df,'timestamp','ts'+datetime.utcnow().strftime('%d%H%M%S'))
        df._add_property('subdir')
        setattr(df,'subdir','working')
        return df



#############################################################
### get_other_files, find_files_in_range, and find_all_files should go in filename.py
### pull out list_other_files, check_dirs_for_files, open_new, and set_wildcards in individual subclasses
#############################################################
    # MLS I check if not num_minutes when setting the checking time to the 
    #     defaults. Previously I had set num_minutes=90 as default in arguments,
    #     so was never getting set to the defaults based on orbital period
    def list_other_files(self,num_minutes=None,all=False,trim=False,extra=None,recursive=False):
        '''list_other_files lists other files matching the current file
            trim=True trims to an odd number of granules 
                (need for viirs rdr converter)
            all=True returns all files including original, 
            all=False does not include the original filename
                called as:
                    TYPEfilename.list_other_files
                    calls filename.get_other_files
                        calls TYPEfilename.set_wildcards
                        calls TYPEfilename.check_dirs_for_files
                    calls filename.find_all_files
                    calls filename.find_files_in_range'''
        si = SatSensorInfo(self.satname,self.sensorname)
        returnfiles = []
        if not si.orbital_period and not num_minutes:
        # If we are not a polar orbiter, we just want to 
        # use a single image time. This includes geostationary
        # AS WELL AS non-individual-satellite type products 
        # (TPW, models, etc)
        # 5 is too much for the rapid scan images. Try 1
        # But still use num_minutes if it was passed...
        # MLS 20161027
        # 3 was still too few minutes to grab everything. 
        #   for full disk ahi. Bump to 5 again ...
            num_minutes = 5
        else:
        # if we are merging swaths together, we are going to need MORE than a full orbital_period
        # to make sure we get all the adjacent swaths.  For global sectors, we can get by with 
        # half an orbital period (because we will get ascending and descending swaths on either 
        # side of the global), but for smaller sectors, we need to get the overpasses from one 
        # orbital period to the next.
            if not num_minutes and extra == 'SWATH':
                #num_minutes=si.orbital_period / 60.0 + (si.orbital_period / 60.0 / 4)
                num_minutes=(5.0/4.0) * (si.orbital_period / 60.0 )
            # If we are merging granules into a swath, we only want half the orbital period, because
            # we just want to create swaths on one side of the globe
            elif not num_minutes:
                num_minutes=(1.0/2.0) * (si.orbital_period / 60.0)

        # I don't think we are ever going to want to do swath composites for geostationary.
        if recursive and not si.geostationary:
            # May need to actually make this recursive, or do more rounds at least.  For very wide sectors, it will only grab the swaths
            # on either side of the swath containing the current granule.  Need to include additional swaths as well. See if this 
            # covers enough for now.
            #if hasattr(self,'optime'):
            #    optime = self.optime
            #    self.optime = '*'
# Still not comfortable making this fully recursive, but at least put it in a 
# single loop so I do not have the same thing typed out 10 times... And makes 
# it easier to repeat additional times. For global/polar images, this will continue 
# to wrap around because every overpass is adjacent to the previous/following 
# overpass. With smaller sectors, it should only do a single set of overpasses
# (the next set will be more than one orbital_period away). We need to figure 
# out a way of cutting it off for global/polar sectors - will be dependent on 
# satellite (revisit time?)
# Also, tried setting optime to * to make sure we caught all the appropriate 
# files to merge, but fixed that issue by naming the swath images using the 
# actual overpass time, not the start data time.

            check_files = [self.name]

            new_files = sorted(self.get_other_files(self,all=all,trim=trim,num_minutes=num_minutes,extra=extra))
            #for ii in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]:
            for ii in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                log.info('        Going through loop '+str(ii))
                check_files1 = []
                if new_files:
                    if new_files[0] not in check_files:
                        check_files1 += [new_files[0]]
                        check_files += [new_files[0]]
                        check_files1 += [new_files[-1]]
                        check_files += [new_files[-1]]
                    for fnstr in check_files1:
                        pfn = ProductFileName(fnstr)
                        #pfn.optime = '*'
                        new_files += self.get_other_files(pfn,all=all,trim=trim,num_minutes=num_minutes,extra=extra)
                    new_files.sort()


            returnfiles = list(set(new_files))
            #if hasattr(self,'optime'):
            #    self.optime = optime
            #if self.name in [new_files[0],new_files[-1]]:
            #    new_files2 = 
        else:
            returnfiles = self.get_other_files(self,all=all,trim=trim,num_minutes=num_minutes,extra=extra)

        return returnfiles

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
        return [self.basedir]

#############################################################
### get_other_files, find_files_in_range, and find_all_files should go in filename.py
### pull out list_other_files, check_dirs_for_files, open_new, and set_wildcards in individual subclasses
#############################################################
    def set_wildcards(self,fnstr):
        '''set_wildcards sets wildcards appropriately for the Given
            filename type. For product filenames, we want any extra 
            and any time and any coverage that matches.
                called as:
                    TYPEfilename.list_other_files
                    calls filename.get_other_files
                        calls TYPEfilename.set_wildcards
                        calls TYPEfilename.check_dirs_for_files
                    calls filename.find_all_files
                    calls filename.find_files_in_range'''
        #print 'fnstr in set_wildcards: '+fnstr
        wildfn = self.open_new(fnstr)
        orig_dt = wildfn.datetime
        #print 'wildfn in set_wildcards: '+wildfn.name

        # Can't tie this to datetime field specifically named time - 
        #   fails with filenames that only define date
        #wildfn.time = '*'
        # Go through all the datetime_fields, looking for the ones that
        #   define %H and %M and %S, and wildcard those individually
        for dt_field in wildfn.datetime_fields.keys():

            new_format = wildfn.datetime_fields[dt_field]

            # If current field contains %H, replace the %H part with *
            if '%H' in new_format:
                # Yields something like %Y%m%d*%M
                new_format = new_format.replace('%H','*')
            if '%M' in new_format:
                new_format = new_format.replace('%M','*')
            if '%S' in new_format:
                new_format = new_format.replace('%S','*')

            # Use original datetime - wildfn won't have a valid datetime
            #    if more than one datetime field have *'s
            # Yields something like 20160621** 
            new_dtstr = orig_dt.strftime(new_format)
            # Set the new wildcarded datetime field (will not have valid datetime now!!)
            setattr(wildfn,dt_field,new_dtstr)
                
        # BUG!!! time MUST be set before extra !!!!!!
        # for some reason the '*' for time in the path does not take until we set another 
        # field after it. (can be any field, does not have to be something in path, can even be date, 
        # if you set time, then date, after setting time only time in filename is *, but after setting date 
        # date in path and filename and time in path and filename are all *)
        wildfn.extra = '*'
        wildfn.coverage = '*'
        #print 'wildfn in set_wildcards: '+wildfn.name
        return wildfn


#############################################################
### get_other_files, find_files_in_range, and find_all_files should go in filename.py
### pull out list_other_files, check_dirs_for_files, open_new, and set_wildcards in individual subclasses
#############################################################
    def delete_old_files(self,extra=None):
        '''delete_old_files removes duplicate files.
            extra is a string that should be included in the 
                filename.extra field of all files that should be deleted
                called as:
                    TYPEfilename.delete_old_files
                    TYPEfilename.list_other_files
                    calls filename.get_other_files
                        calls TYPEfilename.set_wildcards
                        calls TYPEfilename.check_dirs_for_files
                    calls filename.find_all_files
                    calls filename.find_files_in_range'''
        log.info('Trying to delete old files...')
        si = SatSensorInfo(self.satname,self.sensorname)
        # When we are deleting old files, we want to grab 
        # files that are less than half an orbital period 
        # away from the current file. (We want to make sure 
        # we DO NOT get close to the next swath, which would 
        # be half an orbital period away). We only clean up 
        # SWATH files (which go by overpass time) 
        # and FINAL files (which go by start time).
        # SWATH files should be fine, but this may need  
        # tweaking for FINAL files...
        if si.orbital_period is None:
            log.info('File is geostationary, using 1 minutes for finding old files')
            num_minutes = 1
            files = self.list_other_files(all=True,extra=extra,num_minutes=num_minutes)
        else:
            num_minutes=si.orbital_period / 60.0 / 4
            files = self.list_other_files(all=True,extra=extra,num_minutes=num_minutes)
        deleted_fnstrs = []

        try:
            newest_fnstr = files.pop()
        except (IndexError,AttributeError):
            return deleted_fnstrs

        log.info('        Starting deletes...')

        for existing_fnstr in files:
            newest_file = ProductFileName(newest_fnstr)
            existing_file = ProductFileName(existing_fnstr)
            # uses covg in filename to find coverages to only display 
            # latest on web. Add covg to coverage field for easier parsing.
            # MLS 20150622
            newest_covg = float(newest_file.coverage.replace('p','.').replace('covg',''))
            existing_covg = float(existing_file.coverage.replace('p','.').replace('covg',''))
            if existing_covg == newest_covg:
                if newest_file.datetime < existing_file.datetime:
                    try:
                        existing_file.unlink()
                        deleted_fnstrs.append(existing_file.name)
                    except (IOError,OSError),resp:
                        log.error(str(resp)+' Failed DELETING OLD FILE. Someone else did it for us? Skipping')

                elif existing_file.datetime < newest_file.datetime:
                    newest_fnstr = existing_fnstr
                    try:
                        newest_file.unlink()
                        deleted_fnstrs.append(newest_file.name)
                    except (IOError,OSError),resp:
                        log.error(str(resp)+' Failed DELETING OLD FILE. Someone else did it for us? Skipping')
            if existing_covg > newest_covg:
                newest_fnstr = existing_fnstr
                try:
                    newest_file.unlink()
                    deleted_fnstrs.append(newest_file.name)
                except (IOError,OSError),resp:
                    log.error(str(resp)+' Failed DELETING OLD FILE. Someone else did it for us? Skipping')
            elif newest_covg > existing_covg:
                try:
                    existing_file.unlink()
                    deleted_fnstrs.append(existing_file.name)
                except (IOError,OSError),resp:
                    log.error(str(resp)+' Failed DELETING OLD FILE. Someone else did it for us? Skipping')
        return deleted_fnstrs


    def set_fields(self,pf):
        # Will this work for arbitrary date/time fields ?!  (ATCF only has date)
        pf.date = self.date
        pf.time = self.time
        pf.satname = self.satname
        pf.sensorname = self.sensorname
        pf.productname= self.productname
        # set in create_standard()
        pf.dataprovider = self.dataprovider 
        pf.sectorname = self.sectorname
        pf.extra = self.extra
        pf.ext = self.ext
        return pf


class GeoIPSTCProductFileName(GeoIPSProductFileName):
    ext='png'
    data_ext='h5'
    nameformat = GeoIPSnameformat
    fieldsep = stdfieldsep
    fillvalue=stdfillvalue
    noext = stdnoext
    # Note this HAS to be the standard GeoIPSTEMP path, because
    # overlays can't find what they're looking for if it is
    # not where it is looking. This will be solved by using a database.
    geoipstemppathnameformat=GeoIPSTEMPpathnameformat
    pathnameformat=GeoIPSTCpathnameformat
    pathfieldsep = stdpathfieldsep
    pathfillvalue = stdpathfillvalue

    def istype(self):
        # For now, match ATCF and old TC format
        try:
            if 'tc' in self.continent and self.area in ['WPAC','SHEM','ATL','IO','EPAC','CPAC','WP','SH','AL','EP','CP']:
                return True
            else:
                return False
        except:
            return False

class GeoIPSATCFProductFileName(GeoIPSProductFileName):
    ext='png'
    data_ext='h5'
    text_ext='txt'
    nameformat = ATCFnameformat
    fieldsep = atcffieldsep
    fillvalue=stdfillvalue
    noext = stdnoext
    # Note this HAS to be the standard GeoIPSTEMP path, because
    # overlays can't find what they're looking for if it is
    # not where it is looking. This will be solved by using a database.
    geoipstemppathnameformat=GeoIPSTEMPpathnameformat
    pathnameformat=ATCFpathnameformat
    pathfieldsep = stdpathfieldsep
    pathfillvalue = stdpathfillvalue

    def istype(self):
        try:
            if 'tc' in self.continent and self.subarea in ['WP','SH','AL','EP','CP','IO']:
                return True
            else:
                return False
        except:
            return False

class ATCFProductFileName(GeoIPSProductFileName):
    ext='png'
    data_ext='h5'
    text_ext='txt'
    if os.getenv('TCWWW'):
        basedir=os.getenv('TCWWW')
    else:
        basedir=gpaths['GEOIPSFINAL']
    nameformat = ATCFnameformat
    fieldsep = atcffieldsep
    fillvalue=stdfillvalue
    noext = stdnoext
    pathnameformat=ATCFpathnameformat
    pathfieldsep = stdpathfieldsep
    pathfillvalue = stdpathfillvalue

    def istype(self):
        try:
            if 'tc' in self.continent and self.subarea in ['WP','SH','AL','EP','CP','IO']:
                return True
            else:
                return False
        except:
            return False

class AtmosRiverProductFileName(GeoIPSProductFileName):
    ext='jpg'
    if os.getenv('PUBLIC'):
        basedir = os.getenv('PUBLIC')
    else:
        basedir=gpaths['GEOIPSFINAL']
    nameformat = GeoIPSnameformat
    fieldsep = stdfieldsep
    fillvalue=stdfillvalue
    noext = stdnoext
    pathnameformat=atmosriverpathnameformat
    pathfieldsep = atmosriver_pathfieldsep
    pathfillvalue = stdpathfillvalue

    def istype(self):
        # AtmosRiver, PyroCb, and nexsat will match except for the AtmosRiver in self.continent
        try:
            if 'nexsat_www' in self.basedir and 'AtmosRiver' in self.continent:
                return True
            else:
                return False
        except:
            return False

class PyroCBProductFileName(GeoIPSProductFileName):
    ext='jpg'
    if os.getenv('PUBLIC'):
        basedir = os.getenv('PUBLIC')
    else:
        basedir=gpaths['GEOIPSFINAL']
    nameformat = GeoIPSnameformat
    fieldsep = stdfieldsep
    fillvalue=stdfillvalue
    noext = stdnoext
    pathnameformat=pyrocbpathnameformat
    pathfieldsep = pyrocb_pathfieldsep
    pathfillvalue = stdpathfillvalue

    def istype(self):
        # PyroCB, AtmosRiver, and nexsat will match except for the PyroCB in self.continent
        try:
            if 'nexsat_www' in self.basedir and 'PyroCB' in self.continent:
                return True
            else:
                return False
        except:
            return False

class NexsatProductFileName(GeoIPSProductFileName):
    ext='jpg'
    if os.getenv('PUBLIC'):
        basedir = os.getenv('PUBLIC')
    else:
        basedir=gpaths['GEOIPSFINAL']
    nameformat = GeoIPSnameformat
    fieldsep = stdfieldsep
    fillvalue=stdfillvalue
    noext = stdnoext
    pathnameformat=nexsatpathnameformat
    pathfieldsep = stdpathfieldsep
    pathfillvalue = stdpathfillvalue

    def istype(self):
        try:
            # pyrocb, atmosriver, and nexsat will match except for the PyroCB/AtmosRiver in self.continent
            if 'nexsat_www' in self.basedir and 'PyroCB' not in self.continent and 'AtmosRiver' not in self.continent:
                return True
            else:
                return False
        except:
            return False

class SatmetocProductFileName(GeoIPSProductFileName):
    ext='jpg'
    if os.getenv('PRIVATE'):
        basedir = os.getenv('PRIVATE')
    else:
        basedir=gpaths['GEOIPSFINAL']
    nameformat = GeoIPSnameformat
    fieldsep = stdfieldsep
    fillvalue=stdfillvalue
    noext = stdnoext
    pathnameformat=nexsatpathnameformat
    pathfieldsep = stdpathfieldsep
    pathfillvalue = stdpathfillvalue

    def istype(self):
        try:
            if 'nexsat_www' in self.basedir:
                return True
            else:
                return False
        except:
            return False

class TCWebIRVisProductFileName(GeoIPSProductFileName):
    ext='jpg'
    if os.getenv('TCWWW'):
        basedir = os.getenv('TCWWW')
    else:
        basedir=gpaths['GEOIPSFINAL']
    nameformat = GeoIPSnameformat
    fieldsep = stdfieldsep
    fillvalue=stdfillvalue
    noext = stdnoext
    pathnameformat=TCWebIRVispathnameformat
    pathfieldsep = stdpathfieldsep
    pathfillvalue = stdpathfillvalue

    def istype(self):
        try:
            if os.getenv('TCWWW') and os.getenv('TCWWW') in self.basedir:
                return True
            else:
                return False
        except:
            return False

class MetoctiffProductFileName(GeoIPSProductFileName):
    ext = 'jif'
    #sensorname = 'atcf'
    if os.getenv('TCWWW'):
        basedir = os.getenv('TCWWW')
    else:
        basedir=gpaths['GEOIPSFINAL']
    nameformat = Metoctiffnameformat
    fieldsep = stdfieldsep
    fillvalue=stdfillvalue
    pathnameformat=metoctiffpathnameformat
    pathfieldsep = stdpathfieldsep
    pathfillvalue = stdpathfillvalue

    def istype(self):
        try:
            if os.getenv('TCWWW') and os.getenv('TCWWW') in self.basedir:
                return True
            else:
                return False
        except:
            return False

