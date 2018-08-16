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
import os
#import pickle
from datetime import datetime
from collections import OrderedDict
import logging


# Installed Libraries
from IPython import embed as shell
import numpy as np
from lxml import etree, objectify
from pyresample.geometry import AreaDefinition
from pyresample.spherical_geometry import Coordinate
#from pyresample.plot import area_def2basemap


# GeoIPS Libraries
from .XMLNode import XMLNode
from .SectorFileError import SectorFileError, SFAttributeError
from .projections import get_projection
import geoips.productfile as productfile
from geoips.scifile.geometry.plot import area_def2basemap
from geoips.utils.xml_utilities import read_xmlfile
from geoips.utils.log_setup import interactive_log_setup
from geoips.utils.center_to_corner import convert_180_to_360, \
    convert_lat_to_num, convert_lon_to_num

log = interactive_log_setup(logging.getLogger(__name__))

class AllSectorFiles(object):
    def __init__(self,
                 sfnames,
                 sectorlist=None,
                 productlist=None,
                 allstatic=True,
                 allexistingdynamic=False,
                 allnewdynamic=False,
                 scifile=None,
                ):
        self.allstatic=allstatic
        self.allexistingdynamic=allexistingdynamic
        self.allnewdynamic=allnewdynamic
        self.alldynamic = self.allexistingdynamic & self.allnewdynamic
        self.names = sfnames
        self.scifile = scifile
        self.timestamps = {}
        self.sourcefiles = {}
        self.sectorfiles = []
        for sfname in self.names:
            log.debug('sfname: '+sfname)
            self.timestamps = {sfname: datetime.fromtimestamp(os.stat(sfname).st_mtime)}
            sf = XMLSectorFile(sfname,sectorlist,productlist,self.allstatic,self.allnewdynamic,self.allexistingdynamic,scifile=self.scifile)
            self.sectorfiles.append(sf)
            for sectname in sf.sectornames():
                log.debug('sectname: '+sectname)
                self.sourcefiles[sectname] = sfname

    def __repr__(self):
        return "sectorfile.%s(%r)" % (self.__class__.__name__, ' '.join(self.names))

    def __str__(self):
        return "sectorfile.%s(%r)" % (self.__class__.__name__, ' '.join(self.names))

    def __add__(self,other):
        '''Concatenating two sectorfiles together.  Adds other.name to list of 
            sectorfile names in self, and adds all sectors from other to self.'''
        log.debug('        AllSectorFiles + operator') 
        for (name,file) in other.sourcefiles:
            self.sourcefiles[name] = file
        for name in other.names:
            if name not in self.names:
                log.debug('            adding '+name+' to list of sectorfile names')
                self.names.append(name)
                self.sectorfiles.append(XMLSectorFile(name))
                self.timestamps[name] = other.timestamps[name]
        return self

    def open_sectors(self,sectorlist):
        sectors = []
        for sector in sectorlist:
            sect = self.open_sector(sector)
            if sect != None:
                sectors.append(sect) 
        if not sectors:
            return None
        else:
            return sectors

    def check_sectorfile(self,sectorlist=[],productlist=[],sensor=None):
        allsects = {}
        err = '' 

        # We go through the list of sectornames and productnames, and if anything fails we raise an error.
        # If the list is empty, nothing will fail.
        if sectorlist == None:
            sectorlist = []
        if productlist == None:
            productlist = []

        # Fail if no sectorfiles found, nothing will run anyway, and that was probably not the intended operation.
        if self.sectorfiles == []:
            raise SectorFileError('*****No sectorfiles found matching desired sectorlist! Typo in sectorlist?***** '+str(sectorlist))
        for sf in self.sectorfiles:
            sf.check_sectorfile(allsects,err,sectorlist=sectorlist,productlist=productlist)

    def sectornames(self):
        '''Returns a list of all sector names in the current object.'''
        names = []
        for sf in self.sectorfiles:
            names.extend(sf.sectornames())
        return names

    def getsectors(self):
        '''Returns a list of all sector elements in the current object.'''
        allsects = []
        for sf in self.sectorfiles:
            allsects.extend(sf.getsectors())
        return allsects

    def print_available(self,source_name):
        for sf in self.sectorfiles:
            log.interactive('  '+sf.name)
            sf.print_available(source_name)

    def get_available_products(self,source_name):
        allprods= set()
        for sf in self.sectorfiles:
            allprods.update(set(sf.get_available_products(source_name)))
        return list(allprods)

    def get_requested_products(self,source_name,prodlist):
        allprods = set()
        for sf in self.sectorfiles:
            allprods.update(set(sf.get_requested_products(source_name,prodlist)))
        return list(allprods)

    def get_available_sectors(self):
        allsects = set()
        for sf in self.sectorfiles:
            allsects.update(set(sf.get_available_sectors()))
        return list(allsects)

    def get_required_vars(self,source,products=None):
        allvars = set()
        for sf in self.sectorfiles:
            allvars.update(set(sf.get_required_vars(source,products)))
        return list(allvars)

    def get_optional_vars(self,source,products=None):
        allvars = set()
        for sf in self.sectorfiles:
            allvars.update(set(sf.get_optional_vars(source,products)))
        return list(allvars)

    def itersectors(self):
        '''Iterates over all sector elements in the current object.'''
        for sf in self.sectorfiles:
            sects = sf.itersectors()
            while True:
                try:
                    yield sects.next()
                except StopIteration:
                    break

    def open_sector(self, name,checksector=True):
        '''Instantiates a Sector object by short name.'''
        #try:
        #    element = self.root.xpath('sector[@name="%s"]' % name)[0]
        #except IndexError:
        #    return None
        #return Sector(element, self.date, self.time)
        for sf in self.sectorfiles:
            sect = sf.open_sector(name,checksector=checksector)
            if sect != None:
                return sect
            #If no sector found, return None
        return None


class XMLSectorFile(object):
    def __init__(self,
            sectorfile=None,
            sectorlist=None,
            productlist=None,
            allstatic=True,
            allnewdynamic=False,
            allexistingdynamic=False,
            scifile=None,):
        '''
        Reads an XML file containing Sector information for GeoIPS.
        An individual XML file can contain multiple sectors.
        These sectors must have unique names and the combined data contained in the "name" element
            must also be unique.

        +------------+-----------------------------------------------------+
        | Parameters |                                                     |
        +============+=====================================================+
        | sectorfile | A unix file path to an XML file containing sectors. |
        +------------+-----------------------------------------------------+

        +--------------------+---------+------------------------------------------------------------+
        | Keywords           | Default | Description                                                |
        +====================+=========+============================================================+
        | sectorlist         | None    | A list of strings specifying the names of specific         |
        |                    |         | sectors to read from the input sectorfile.                 |
        +--------------------+---------+------------------------------------------------------------+
        | allstatic          | True    | Read all sectors available in $GEOIPS/sectorfiles/static   |
        +--------------------+---------+------------------------------------------------------------+
        | allexistingdynamic | False   | Read all existing dynamic sectors (e.g. tropical cyclones) |
        +--------------------+---------+------------------------------------------------------------+
        | allnewdynamic      | False   | Read all dynamic sectors. ??? Please fix description...    |
        +--------------------+---------+------------------------------------------------------------+
        '''


        if sectorfile is not None:
            if not os.path.isfile(sectorfile):
                raise IOError('File does not exist: %s' % sectorfile)
            #Store input parameters.
            self.name = sectorfile
            self.tree = read_xmlfile(sectorfile, do_objectify=True)
            self.timestamp = datetime.fromtimestamp(os.stat(sectorfile).st_mtime)
            self.root = self.tree.getroot()
        else:
            self.name = 'NewFile.xml'
            self.root = objectify.XML('<?xml version="1.0" standalone="no"?>\n'+
                    '<!DOCTYPE sector_file SYSTEM "%s/sectorfiles.dtd">\n' % os.getenv('SECTORFILEPATH_BETA')+
                    '<sector_file xmlns:py="http://codespeak.net/lxml/objectify/pytype">\n'+
                    '</sector_file>\n'
                    )
            self.tree = self.root
            self.timestamp = datetime.now()


        self.names = [self.name] #Used when merging into AlLSectorFiles instances
        self.__sectorlist = sectorlist
        self.__productlist = productlist
        #I'd like to rename these to hide them, but I'm not sure if they're used elsewhere.
        self.allstatic=allstatic
        self.allexistingdynamic=allexistingdynamic
        self.allnewdynamic=allnewdynamic
        self.scifile=scifile

        #If both allexistingdynamic and allnewdynamic are True, then set alldynamic to True
        self.alldynamic = False
        if self.allexistingdynamic is True or self.allnewdynamic is True:
            self.alldynamic = True

        self._sectors = {}

    def __repr__(self):
        return "sectorfile.%s(%r)" % (self.__class__.__name__, self.name)

    def reset(self):
        '''Resets the object to its previous saved state.'''
        self.__init__(self.name)

    def check_sectorfile(self,allsects={},err='',sectorlist=[],productlist=[]):
        '''
        Check the input XML file to be sure that:
            1. No sectors are repeated.
            2. All requested sectors can be found in the sectorfile.
        '''
        # MLS If sectorlist/productlist passed as None, reset to []
        # This was failing when calling command line with just --sectorfiles
        if not sectorlist:
            sectorlist = []
        if not productlist:
            productlist = []
        availsects = {}
        log.debug('      checking sectorfile: '+self.name)

        sects = self.getsectors() 
        sectnames = [xx.lower() for xx in self.sectornames()]

        #Check for any missing sectors
        for sect in sectorlist:
            if sect not in sectnames:
                err += 'Sector '+sect+' not found! Spelled wrong? Available sectors: '+str(sectnames)+'\n'

        #Check to be sure no sectors are repeated
        for sect in sects:
            log.debug('        checking sector: '+sect.name)
            if sect.name in allsects and not sect.isdynamic:
                (desig,sourcefile) = allsects[sect.name].split(' ')
                err += '''
                       Sector '%s' used more than once: 
                       %-25s%-50s%s 
                       %-25s%-50s%s'''\
                        %(sect.name,sect.name,sect.name_info.desig,sect.sourcefile,sect.name,desig,sourcefile)
            #If the sector is dynamic, it can be repeated so long as it has a different datetime
            elif sect.isdynamic:
                allsects[sect.name+'.'+sect.dynamic_datetime.strftime('%Y%m%d.%H%M')] = sect.name_info.desig+' '+sect.sourcefile
                availsects[sect.name+'.'+sect.dynamic_datetime.strftime('%Y%m%d.%H%M')] = sect.name_info.desig+' '+sect.sourcefile
            else:
                allsects[sect.name] = sect.name_info.desig+' '+sect.sourcefile
                availsects[sect.name] = sect.name_info.desig+' '+sect.sourcefile
        if err:
            err = 'Invalid sector file entry: \n'+err
            raise SectorFileError(err)
        sorted_list = [x for x in availsects.iteritems()]
        sorted_list.sort(key=lambda x: x[1])
        sectors_str = [] 
        for val in sorted_list:
            (desig,sourcefile) = val[1].split(' ')
            sectors_str.append('%-25s%-50s%s'%(val[0],desig,sourcefile))
        bigindent= '\n'+' '*10
        log.interactive('Available sectors:'+bigindent+bigindent.join(sectors_str))

    @property
    def sectors(self):
        for name in self._sectors.keys():
            if name not in self.sectornames():
                self._sectors.pop(name)
        for name in self.sectornames():
            if name not in self._sectors.keys():
                self._sectors[name] = self.open_sector(name)
        return self._sectors

    def sectornames(self):
        '''Returns a list of all sector names in the current object.
            Skip things not in self.__sectorlist'''
        sectornames = self.root.xpath('sector/@name')
        #    element = self.root.xpath('sector[@name="%s"]' % name)[0]
        #elements = self.root.xpath('sector')
        #for element in elements:
        #    if element.attrib['name'].lower() == name.lower():
        #        sect = Sector(element, self.timestamp,self.name,self.scifile)
        allsectornames = []
        for sectorname in sectornames:
            elt = self.root.xpath('sector[@name="%s"]' % sectorname)[0]
            sect = Sector(elt,self.timestamp,self.name,self.scifile)
            if self.check_sector(sect) == True:
                allsectornames.append(sectorname.lower())
        return allsectornames

    def print_available(self,source_name):
        for sectname in self.get_available_sectors():
            log.interactive('    Sector "'+sectname+'"')
            if source_name.lower() in [ii.lower() for ii in self.open_sector(sectname,checksector=False).products.keys()]:
                log.interactive('        Available "'+source_name+'" products: ')
                for prodname in self.open_sector(sectname,checksector=False).products[source_name]:
                    log.interactive('          '+prodname)
            else:
                log.interactive('        NO Available "'+source_name+'" products for sector "'+sectname+'"')

    def get_available_products(self,source_name):
        #allsects = set([ii.name.lower() for ii in self.getsectors(checksector=False) if self.scifile and self.scifile.source_name in ii.products.keys()])
        allprods = []
        for ii in self.getsectors(checksector=False):
            allprods += ii.get_available_products(source_name)
        return list(set(allprods))

    def get_requested_products(self,source_name,prodlist):
        #allsects = set([ii.name.lower() for ii in self.getsectors(checksector=False) if self.scifile and self.scifile.source_name in ii.products.keys()])
        allprods = []
        for ii in self.getsectors(checksector=False):
            allprods += ii.get_requested_products(source_name,prodlist)
        return list(set(allprods))

    def get_available_sectors(self):
        #allsects = set([ii.name.lower() for ii in self.getsectors(checksector=False) if self.scifile and self.scifile.source_name in ii.products.keys()])
        allsects = set([ii.name.lower() for ii in self.getsectors(checksector=False)])
        return list(allsects)

    def get_required_vars(self,source,products=None):
        allvars = set()
        for sect in self.getsectors():
            allvars.update(set(sect.get_required_vars(source,products)))
        return list(allvars)

    def get_optional_vars(self,source,products=None):
        allvars = set()
        for sect in self.getsectors():
            allvars.update(set(sect.get_optional_vars(source,products)))
        return list(allvars)

    def getsectors(self,checksector=True):
        '''Returns a list of all sector elements in the current object.'''
        elements = self.root.xpath('sector')
        allsects = []
        for element in elements:
            sect = Sector(element,self.timestamp,self.name,self.scifile)
            if not checksector:
                allsects.append(sect)
            elif self.check_sector(sect) == True:
                allsects.append(sect)
            # Do we want to always check_sector, and comment out
            # above if/else ?
            #if self.check_sector(sect):
            #    allsects.append(sect)
        return allsects
            
    def itersectors(self):
        '''Iterates over all sector elements in the current object.'''
        ind = 1
        while True:
            try:
                #Grab the element at position "ind"
                element = self.root.xpath('sector[%r]' % ind)[0]
                ind += 1
                sect = Sector(element,self.timestamp,self.name,self.scifile)
                if self.check_sector(sect) == True:
                    yield sect
            except IndexError:
                break

    def check_sector(self,sect):

        productlist = []
        sourcekeys = []
        sourceprods = []
        if self.__productlist:
            productlist = [ii.lower() for ii in self.__productlist]
        sourcekeys = [ii.lower() for ii in sect.products.keys()]
        if self.scifile and self.scifile.source_name in sect.products.keys():
            sourceprods = [ii.lower() for ii in sect.products[self.scifile.source_name]]

        # To revert to old way, get rid of everything but these two lines, and return True
        # If __sectorlist is defined, make sure current sector is in sectorlist.
        if self.__sectorlist != None and sect.name.lower() not in [x.lower() for x in self.__sectorlist]:
            return False

        # If sectorlist and scifile are both defined, make sure there are actually any products of type source 
        # defined for current sector.
        elif self.__sectorlist and self.scifile and self.scifile.source_name  not in sourcekeys:
            #log.interactive('    No products for source "'+self.scifile.source_name+'" defined for sector "'+sect.name+'"')
            return False
        # If productlist and scifile are both defined, make sure there are actually requested products type source
        # defined for current sector
        elif productlist and sourceprods and not (set(productlist) & set(sourceprods)):
            #log.interactive('    Products "'+' '.join(self.__productlist)+'" not defined for sector '+sect.name+' (only "'+' '.join(sect.products[self.scifile.source_name])+'" defined)')
            return False
        # If we managed to get through all that, we should be good.
        return True

    def open_sectors(self,sectorlist):
        sectors = []
        for sector in sectorlist:
            sect = self.open_sector(sector)
            if sect != None:
                sectors.append(sect) 
        if not sectors:
            return None
        else:
            return sectors

    def open_sector(self, name, checksector=True):
        '''Instantiates a Sector object by short name.'''
        #try:
        #    element = self.root.xpath('sector[@name="%s"]' % name)[0]
        #except IndexError:
        #    return None
        #return Sector(element, self.date, self.time)
        elements = self.root.xpath('sector')
        for element in elements:
            if element.attrib['name'].lower() == name.lower():
                sect = Sector(element, self.timestamp, self.name, self.scifile)
                if not checksector:
                    return sect
                elif self.check_sector(sect) == True:
                    return sect
                # Do we want to always check_sector, and comment out 
                # above if/else ?
                #if self.check_sector(sect):
                #    return sect
        #If no sector found, return None
        return None

    def append(self, element):
        '''Appends a new sector element to the end of the root element.'''
        try:
            #log.info(element)
            element = element.node
        except AttributeError:
            pass
        if element.tag == 'sector':
            self.root.append(element)
        else:
            raise SectorFileError('''Can only append sector elements to root element.  
                                  Given %s element.''' % element.tag)

    def extend(self, element_list):
        '''Appends a list of sector elements to the end of the root element.'''
        for element in element_list:
            self.append(element)


    def remove(self, name):
        '''Removes the a sector from the current object.  Sector is found
        by its "name" attribute.'''
        element = self.root.xpath('sector[@name="%s"]' % name)
        try:
            self.root.remove(element[0])
        except ValueError:
            log.warning('Cannot remove sector named %s.  Does not exist.' % name)

    def pop(self, name):
        '''Pops a sector off the stack of sectors and returns that sector.'''
        sect = self.open_sector(name)
        self.remove(name)
        return sect

class Sector(object):
    def __init__(self, sector_element, timestamp=None, sourcefile=None,scifile=None):
        #Initialize simple attributes
        self.node = sector_element
        self.timestamp = timestamp
        self.sourcefile = sourcefile
        self.scifile = scifile
        try:
            self.sources = self.Sources(self.node.source, self.scifile)
        except AttributeError:
            self.sources = None
        #Initialize SourceInfo node
        #Used to store information about the source of a dynamic sector's information
        try:
            self.source_info = self.SourceInfoNode(self.node.source_info,self.scifile)
        except AttributeError:
            self.source_info = None
        #Initialize TCInfo node for TC sectors
        #Contains storm info like pressure, wind_speed, and location
        try:
            self.tc_info = self.TCInfoNode(self.node.tc_info,self.scifile)
        except AttributeError:
            self.tc_info = None
        #Initialize VolcanoInfo node for volcano sectors
        #Contains volcano info like elevation, plume_heigh, wind_speed, and location
        try:
            self.volcano_info = self.VolcanoInfoNode(self.node.volcano_info,self.scifile)
        except AttributeError:
            self.volcano_info = None
        try:
            self.pyrocb_info = self.PyroCBInfoNode(self.node.pyrocb_info,self.scifile)
        except AttributeError:
            self.pyrocb_info = None
        try:
            self.atmosriver_info = self.PyroCBInfoNode(self.node.atmosriver_info,self.scifile)
        except AttributeError:
            self.atmosriver_info = None
        #Initialize NameNode which is required for all sectors
        #Contains a six level naming structure for the sector
        #   Continent, Country, Area, Subarea, State, City
        self.name_info = self.NameNode(self.node.name,self.scifile)
        #Initialize PlotInfo node which is required for all sectors
        #Defines information about hwo the sector should be plotted such as:
        #   Grid line spacing, minimum coverage, map resolution
        self.plot_info = self.PlotInfoNode(self.node.plot_info,self.scifile)
        #Initialize AreaInfo node
        #Required for all Sectors
        #Contains all information required to describe the plot area
        self.area_info = self.AreaInfoNode(self.node.area_info,self.scifile)
        #Initialize PlotObjects node
        if hasattr(self.node, 'plot_objects'):
            self.plot_objects = self.PlotObjectsNode(self.node.plot_objects,self.scifile)
        else:
            self.plot_objects = None

    def __repr__(self):
        return "%s(%r,sourcefile=%s,timestamp=%s)" % (self.__class__.__name__, self.name,self.sourcefile,str(self.timestamp))

    def __str__(self):
        objectify.deannotate(self.node)
        return etree.tostring(self.node, pretty_print=True)

    def eval_att(self,path):
        try:
            # if eval doesn't work, just return the string
            return eval(self.node.xpath(path)[0])
        except:
            return self.node.xpath(path)[0]

    @property
    def name(self):
        '''Getter method for sector's short name.'''
        self._name = self.node.xpath('@name')[0]
        return self._name
    @name.setter
    def name(self, val):
        '''Setter method for sector's short name.'''
        self.node.set('name', val)

    @property
    def sector_name_product(self):
        # sector_name used in filenames, for merging, etc (ie, allows multiple TCs for single tc mint reader)
        # Use sector_name_product if available in scifile metadata.
        if self.scifile and 'sector_name_product' in self.scifile.metadata['top'].keys() and self.scifile.metadata['top']['sector_name_product']:
            return self.scifile.metadata['top']['sector_name_product']
        else:
            # Default to name attribute if sector_name_product attribute is not defined in reader metadata
            return self.name

    @property
    def sector_name_display(self):
        # sector_name_display used in titles, legends, etc. Not referenced internally to GeoIPS.
        if self.eval_att('@sector_name_display'):
            # If defined in xml, use that.
            return self.eval_att('@sector_name_display')
        elif self.scifile and 'sector_name_display' in self.scifile.metadata['top'].keys() and self.scifile.metadata['top']['sector_name_display']: 
            # If not defined in xml, but defined in scifile metadata, use scifile metadata.
            return self.scifile.metadata['top']['sector_name_display']
        else:
            # Default to sector.name if sector_name_display attribute is not defined in xml or scifile metadata
            return self.name

#######################################
# Properties for node dictionaries
#   name_dict
#   area_dict
#######################################
    @property
    def name_dict(self):
        '''Dictionary of sector name values.'''
        self._name_dict = self.name_info.name_dict
        return self._name_dict
    @name_dict.setter
    def name_dict(self, val):
        '''Setter for dictionary of sector name values.'''
        self.name_info.name_dict = val
    # THIS WILL NOT WORK!!! Need to use with min/max lat/lon
    # @property
    # def area_dict(self):
    #     '''Dictionary of area information.'''
    #     self._area_dict = self.area_info.area_dict
    #     return self._area_dict
    # @area_dict.setter
    # def area_dict(self, val):
    #     self.area_info.area_dict = val

    @property
    def basemap(self):
        '''Returns a basemap for the sector instance.'''
        # MLS we need to pass the old arguments to basemap - resolution
        #     was not getting set (along with fix_aspect and suppress_ticks)
        if not hasattr(self, '_basemap'):
            self._basemap = area_def2basemap(self.area_definition,
                            fix_aspect=False,   
                            suppress_ticks=True,
                            resolution=self.plot_info.map_resolution[0].lower())
        return self._basemap
# Pickle basemap instances for each sector and reload.
# Not sure this will help over all - takes about half as long 
# to read in as to create new basemap instance. I/O might end 
# up being limiting factor. Arctic sectors make REALLY big basemap 
# instances (400MB for CICElarge, 6MB for california)
#        if not hasattr(self,'_basemap'):
#            log.info('        setting sector.basemap...')
#            existing_bm = StandardAuxDataFileName.find_existing_file(
#                                sectorname=self.name,
#                                extdatatype='basemap',
#                                ext='pkl',
#                                retobj=True)
#            new_bm = StandardAuxDataFileName.frominfo(sectorname=self.name,extdatatype='basemap',ext='pkl')
#            source_dt = datetime.fromtimestamp(os.stat(self.sourcefile).st_mtime)
#            if not existing_bm or (existing_bm.datetime and existing_bm.datetime < source_dt):
#                log.info('Need to recreate basemap! Sectorfile dt: '+
#                            str(source_dt)+' is newer than basemap pickle dt: '+
#                            str(existing_bm)+' new file: '+new_bm.name) 
#                self._basemap = area_def2basemap(self.area_definition,
#                            fix_aspect=False,   
#                            suppress_ticks=True,
#                            resolution=self.plot_info.map_resolution[0].lower())
#                log.info('Writing Basemap pickle to: '+new_bm.name)
#                new_bm.makedirs()
#                pickle.dump(self._basemap,open(new_bm.name,'wb'))
#                log.info('Basemap pickle written to: '+new_bm.name)
#                new_bm.delete_old_files()
#            else:
#                log.info('Loading basemap pickle '+existing_bm.name)
#                self._basemap = pickle.load(open(existing_bm.name,'rb'))
#
#            log.info('        done setting sector.basemap...')
#        else:
#            log.info('_basemap already set, just return')

    @property
    def area_definition(self):
        '''An area definition for use with pyresample for the current sector.'''
        pr_proj = self.area_info.proj4_projection
        #shell()
        #log.info('Using center lat/lon: '+str(self.area_info.center_lat_float)+' '+str(self.area_info.center_lon_float))
        #log.info('Using min/max lon: '+str(self.area_info.min_lon_float)+' '+str(self.area_info.max_lon_float))
        #log.info('Using min/max lat: '+str(self.area_info.min_lat_float)+' '+str(self.area_info.max_lat_float))
        #log.info('Using pixel width/height: '+str(self.area_info.proj4_pixel_width)+' '+str(self.area_info.proj4_pixel_height))
        #log.info('Using width/height: '+str(self.area_info.width)+' '+str(self.area_info.height))
        #log.info('Using num samples/lines: '+str(self.area_info.num_samples)+' '+str(self.area_info.num_lines))
        # pyresample uses eqc, basemap uses cyl. Need a better way...
        if pr_proj == 'cyl':
            pr_proj = 'eqc'
        proj4_dict = {'proj':pr_proj,
                      'a': 6371228.0,
                      'lat_0':self.area_info.center_lat_float,
                      'lon_0':self.area_info.center_lon_float,
                      'units':'m',
                     }
        area_left = -self.area_info.width/2.0
        area_right = self.area_info.width/2.0
        area_bot = -self.area_info.height/2.0
        area_top = self.area_info.height/2.0
        area_extent = (area_left, area_bot, area_right, area_top)
        #log.info('area_extent: '+str(area_extent))
        area_def = AreaDefinition(self.name,
                                  self.name,
                                  self.name_info.desig,
                                  proj4_dict,
                                  y_size=self.area_info.num_lines_calc,
                                  x_size=self.area_info.num_samples_calc,
                                  area_extent=area_extent,
                                 )
        return area_def


#######################################
# Getter methods for derived quantities
#   date
#   min_cover
#   projection
#######################################
#    @property
#    def sectorfile_date(self):
#        '''Modification date for sectorfile'''
#        self._date = os.stat(self.node.base).st_mtime
#        return self._date

    #This doesn't work!  NEED TO FIX!!!
    #@property
    #def min_cover(self):
    #    '''Minimum coverage allowed for the sector.  Takes into account
    #    any overrides from satellite or product elements.'''
    #    self._min_cover = get_min_cover(self.node)
    #    return self._min_cover
    #@min_cover.setter
    #def min_cover(self):
    #    set_min_cover(self.node)

    @property
    def min_total_cover(self):
        '''Minimum coverage allowed for the sector.  Takes into account
        any overrides from satellite or product elements.'''
        if not hasattr(self, '_min_total_cover'):
            try:
                self._min_total_cover = self.node.plot_info.min_total_cover
            except AttributeError:
                self._min_total_cover = 40
        return self._min_total_cover

    def run_on_source(self,source_name):
        if source_name not in self.source_list and 'ALLSOURCES' not in self.source_list:
            return False
        return True

    @property
    def source_list(self):
        '''A list of the sources this sector can make use of.'''
        if not hasattr(self, '_source_list'):
            self._source_list = self.node.xpath('source/@name')
        return self._source_list

    @property
    def products(self):
        '''A dict containing information on which products should be
        produced from which data sources.'''
        if not hasattr(self, '_products'):
            products = {}
            for elem in self.node.findall('source'):
                sourcename = elem.xpath('@name')[0]
                products[sourcename] = elem.xpath('product/@name')
            self._products = products
        return self._products

    def get_available_products(self,source_name):
        # Allow ALLSOURCES as source name, and ALLPRODUCTS as product name to do EVERYTHING
        if 'ALLSOURCES' in self.source_list and 'ALLPRODUCTS' in self.products['ALLSOURCES']:
            return [xx.lower() for xx in productfile.get_sensor_productnames(source_name)]
        # Also allow source_name specified, but ALLPRODUCTS in list of products to run ALL PRODUCTS.
        elif source_name in self.products.keys() and 'ALLPRODUCTS' in self.products[source_name]:
            return [xx.lower() for xx in productfile.get_sensor_productnames(source_name)]
        elif source_name in self.products.keys():
            return [xx.lower() for xx in self.products[source_name]]
        else:
            return []

    def get_requested_products(self,source_name,requested_product_names):
        # If special ALLSOURCES and ALLPRODUCTS key words are used, all available products are valid.        
        avail_products = self.get_available_products(source_name)
        #print avail_products
        #print requested_product_names
        #print set(avail_products)&set(requested_product_names)
        # If no products were requested, return all
        if not requested_product_names:
            return avail_products
        else:
            return list(set(avail_products)&set(requested_product_names))

    def get_required_vars(self, source, products=None):
        '''Returns a list of the variables required from the input data source
        for all of the products it can produce for the current sector.'''
        requested = self.get_requested_products(source,products)
        
        if requested:
            pf = productfile.open2(source, requested)
            if pf:
                return pf.get_required_source_vars(source)
            else:
                raise productfile.ProductFileError.ProductFileError
        else:
            return []

    def get_optional_vars(self, source, products=None):
        '''Returns a list of the variables required from the input data source
        for all of the products it can produce for the current sector.'''
        requested = self.get_requested_products(source,products)
        
        if requested:
            pf = productfile.open2(source, requested)
            if pf:
                return pf.get_optional_source_vars(source)
            else:
                raise productfile.ProductFileError.ProductFileError
        else:
            return []

    def get_required_geolocation_vars(self, source, products=None):
        '''Returns a list of the variables required from the input data source
        for all of the products it can produce for the current sector.'''
        if products is not None:
            avail_products = set([prod.lower() for prod in self.products[source]])
            products = set([prod.lower() for prod in products])
            requested = products.intersection(avail_products)
            diff_test = products.difference(requested)
            if len(diff_test) > 0:
                raise ValueError('Requested products not found.  Missing %s.' % diff_test)
            requested = list(requested)
        else:
            requested = self.products[source]

        pf = productfile.open2(source, requested)
        if pf:
            return pf.get_required_source_geolocation_vars(source)
        else:
            raise productfile.ProductFileError.ProductFileError


    #This stuff can be used for developing GUIs.  Turned off for now.

    #def add_product(self, satname, prodname):
    #    '''Adds a product to the current sector by source name and product name as strings'''
    #    if self.has_satellite(satname) is False:
    #        sat_node = self.add_satellite(satname)
    #    else:
    #        sat_node = self.find_satellite(satname)
    #    prodname = prodname[0].upper() + prodname[1:]
    #    new_product = etree.Element('product', name=prodname)
    #    sat_node.append(new_product)
    #    return new_product

    #def add_satellite(self, satname):
    #    if self.has_satellite(satname) is False:
    #        new_sat = etree.Element('satellite', name=satname.lower())
    #        self.node.append(new_sat)
    #        return new_sat
    #    else:
    #        raise SectorFileError('Satellite node already exists')

    #def del_product(self, satname, product):
    #    '''Deletes a product from the current cetor by sensor name and product name as strings.'''
    #    if self.has_satellite(satname) is False:
    #        raise SectorFileError('Cannot delete product from current sector.  ' +
    #                              '%s sensor does not exist in %s  sector.' % (satname, self.name))
    #    else:
    #        sat_elem = self.find_satellite(satname)

    #    sat_products = sat_elem.xpath('product')
    #    product_match = []
    #    for elem in sat_products:
    #        if elem.tag == 'product' and elem.attrib['name'].lower() == product.lower():
    #            product_match.append(elem)
    #    if len(product_match) == 0:
    #        raise SectorFileError('Cannot delete product from current sector.  ' +
    #                              '%s product does not exist in %s sector.' % (product, self.name))
    #    elif len(product_match) > 1:
    #        raise SectorFileError('This should never happen!'
    #                              'Multiple products found with name %s for sensor %s in sector %s' %
    #                              (product, sensor, sector))
    #    else:
    #        sat_elem.remove(product_match[0])

    #    if sat_elem.countchildren() == 0:
    #        self.del_satellite(satname)

    #def del_satellite(self, satname):
    #    '''Deletes a satellite from the current sector by sensor name as a string.'''
    #    sat_elem = self.find_satellite(satname)
    #    if sat_elem is None:
    #        raise SectorFileError('Cannot delete sensor from sector.  ' +
    #                              '%s sensor does not exist in current sector.' % satname)
    #    else:
    #        self.node.remove(sat_elem)




#######################################
# Internal classes
#   MasterInfoNode
#   NameNode
#   PlotInfoNode
#######################################

    class AreaInfoNode(XMLNode):
        def __init__(self, area_info_node, scifile=None):
            super(Sector.AreaInfoNode, self).__init__(area_info_node,scifile=scifile)
            #if self.basemap_projection not in ['spstere', 'npstere']:
            #    self.lons_180_to_360()
            self.__initialized = True
            self.scifile = scifile

            # THIS WILL NOT WORK!!!!!!!!!!!!!!!
            # need to use min/max lat/lon
            # self.area_parts = ['center_lat',
            #                    'center_lon',
            #                    'num_lines',
            #                    'num_samples',
            #                    'pixel_width',
            #                    'pixel_height',
            #                    'projection'
            #                     ]

            #Should think about how to do this...

            #self.master_parts = ['min_lat',
            #                         'max_lat',
            #                         'min_lon',
            #                         'max_lon',
            #                         'num_lines',
            #                         'num_samples',
            #                        ]

        # THIS WILL NOT WORK!!!!!!!!!!!!!!!
        # need to use min/max lat/lon
        # @property
        # def area_dict(self):
        #     self._area_dict = OrderedDict()
        #     for part in self.area_parts:
        #         self._area_dict[part] = getattr(self, part)
        #     return self._area_dict

        # This needs to be in METERS
        @property
        def width(self):
            if hasattr(self, 'proj4_pixel_width') and hasattr(self,'num_samples'):
                self._width = self.num_samples_calc * self.proj4_pixel_width * 1000
                return self._width
            elif hasattr(self,'proj4_pixel_width') and hasattr(self,'min_lon'):
                earth_radius_km = 6372.795
                if self.proj4_projection == 'cyl':
                    # Find the maximum span, which will be at the equator.
                    latval = 0
                else:
                    # Above didn't work so well for stere in N Hem. (PCB Siberia)
                    # Need to take lat closest to equator.
                    latval = min(abs(self.max_lat_float),
                                 abs(self.min_lat_float))
                left = Coordinate(lon=float(self.min_lon_float),
                                  lat=float(latval))
                right = Coordinate(lon=float(self.max_lon_float),
                                   lat=float(latval))
                lon_dist = left.distance(right)*earth_radius_km 
                self._width = lon_dist*1000
                return self._width
            else:
                return None

        # This needs to be in METERS
        @property
        def height(self):
            if hasattr(self, 'proj4_pixel_height') and hasattr(self,'num_lines'):
                self._height = self.num_lines_calc * self.proj4_pixel_height * 1000
                return self._height
            elif hasattr(self,'proj4_pixel_height') and hasattr(self,'min_lon'):
                earth_radius_km = 6372.795
                ul = Coordinate(lon=float(self.min_lon_float),lat=float(self.max_lat_float))
                ll = Coordinate(lon=float(self.min_lon_float),lat=float(self.min_lat_float))
                lat_dist = ul.distance(ll)*earth_radius_km 
                self._height = lat_dist*1000
                return self._height
            else:
                return None

        # min_lat, etc get set automatically from the sectorfile.
        # We need float versions anyway, and we can't set min_lat, etc as
        #   properties, so use the float versions. We know the float versions
        #   will ALWAYS be set, regardless of what was specified in the 
        #   sectorfile.
        @property 
        def min_lat_float(self):
            if hasattr(self,'min_lat') and self.min_lat == 'FROMDATA':
                self._min_lat_float = min([(geovar['Latitude']).min() for geovar in [ds.geolocation_variables for ds in self.scifile.datasets.values()]])
                log.info('    Setting min_lat from data: '+str(self._min_lat_float))
                return self._min_lat_float
            elif hasattr(self,'min_lat'):
                self._min_lat_float = convert_lat_to_num(self.min_lat)
                return self._min_lat_float
            else:
                return None

        @property 
        def min_lon_float(self):
            if hasattr(self,'min_lon') and self.min_lon == 'FROMDATA':
                for ds in self.scifile.datasets.values():
                    geovar = ds.geolocation_variables['Longitude']
                    # Crosses dateline
                    if abs(geovar.min()) > 179 and abs(geovar.max()) > 179:
                        self._min_lon_float = np.extract(geovar>0,geovar).min()
                    else:
                        self._min_lon_float = geovar.min()
                log.info('    Setting min_lon from data: '+str(self._min_lon_float))
                return self._min_lon_float
            elif hasattr(self,'min_lon'):
                self._min_lon_float = convert_lon_to_num(self.min_lon)
                return self._min_lon_float
            else:
                return None


        @property 
        def max_lat_float(self):
            if hasattr(self,'max_lat') and self.max_lat == 'FROMDATA':
                self._max_lat_float = max([(geovar['Latitude']).max() for geovar in [ds.geolocation_variables for ds in self.scifile.datasets.values()]])
                log.info('    Setting max_lat from data: '+str(self._max_lat_float))
                return self._max_lat_float
            elif hasattr(self,'max_lat'):
                self._max_lat_float = convert_lat_to_num(self.max_lat)
                return self._max_lat_float
            else:
                return None

        @property 
        def max_lon_float(self):
            if hasattr(self,'max_lon') and self.max_lon == 'FROMDATA':
                for ds in self.scifile.datasets.values():
                    geovar = ds.geolocation_variables['Longitude']
                    # Crosses dateline
                    if abs(geovar.min()) > 179 and abs(geovar.max()) > 179:
                        self._max_lon_float = np.extract(geovar<0,geovar).max()
                    else:
                        self._max_lon_float = geovar.max()
                log.info('    Setting max_lon from data: '+str(self._max_lon_float))
                return self._max_lon_float
            elif hasattr(self,'max_lon'):
                self._max_lon_float = convert_lon_to_num(self.max_lon)
                return self._max_lon_float
            else:
                return None

        @property
        def proj4_pixel_height(self):
            if not hasattr(self,'pixel_height') and hasattr(self,'min_lon'):
                earth_radius_km = 6372.795
                ul = Coordinate(lon=float(self.min_lon_float),lat=float(self.max_lat_float))
                ll = Coordinate(lon=float(self.min_lon_float),lat=float(self.min_lat_float))
                lat_dist = ul.distance(ll)*earth_radius_km 
                self._proj4_pixel_height = lat_dist / self.num_samples_calc
                self.pixel_height = self._proj4_pixel_height
            elif hasattr(self,'pixel_height'):
                # This was failing on pf.resolution.is_integer() in 
                # utils/path/productfilename.py (when checking precision
                # for resolution in file path). So make sure we Store 
                # these as float
                # This is the value we will always actually use, not
                # pixel_width/pixel_height
                self._proj4_pixel_height = float(self.pixel_height)
            else:
                self._proj4_pixel_height = None
            return self._proj4_pixel_height

        @property
        def proj4_pixel_width(self):
            if not hasattr(self,'pixel_width') and hasattr(self,'min_lon'):
                earth_radius_km = 6372.795
                ul = Coordinate(lon=float(self.min_lon_float),lat=float(self.max_lat_float))
                ur = Coordinate(lon=float(self.max_lon_float),lat=float(self.max_lat_float))
                lon_dist = ul.distance(ur)*earth_radius_km 
                self._proj4_pixel_width = lon_dist / self.num_lines_calc
                self.pixel_width = self._proj4_pixel_width
            elif hasattr(self,'pixel_width'):
                # This was failing on pf.resolution.is_integer() in 
                # utils/path/productfilename.py (when checking precision
                # for resolution in file path). So make sure we Store 
                # these as float
                # This is the value we will always actually use, not
                # pixel_width/pixel_height
                self._proj4_pixel_width = float(self.pixel_width)
            else:
                self._proj4_pixel_width = None
            return self._proj4_pixel_width

        @property
        def num_lines_calc(self):
            if hasattr(self,'num_lines') and self.num_lines == 'FROMDATA':
                self._num_lines_calc = min([ds.shape[1] for ds in self.scifile.datasets.values()])
            elif hasattr(self,'num_lines'):
                self._num_lines_calc = int(self.num_lines)
            elif hasattr(self,'height'):
                self._num_lines_calc = int((self.height/1000) / self.proj4_pixel_height )
            else:
                self._num_lines_calc = None
            return self._num_lines_calc

        @property
        def num_samples_calc(self):
            if hasattr(self,'num_samples') and self.num_samples == 'FROMDATA':
                self._num_samples_calc = min([ds.shape[0] for ds in self.scifile.datasets.values()])
            elif hasattr(self,'num_samples'):
                self._num_samples_calc = int(self.num_samples)
            elif hasattr(self,'width'):
                self._num_samples_calc = int((self.width/1000) / self.proj4_pixel_width)
            else:
                self._num_samples_calc = None
            return self._num_samples_calc

        @property
        def display_resolution(self):
            ''' display_resolution is the string we use to output in 
                path names and filenames and plot labels'''
            if self.proj4_pixel_width > self.proj4_pixel_height:
                self._display_resolution = self.proj4_pixel_width
            else:
                self._display_resolution = self.proj4_pixel_height 
            # is_integer only defined for floats. Store proj4_pixel_width/height
            # as float in sectorfile/xml.py
            if self._display_resolution > 5 or self._display_resolution.is_integer():
                self._display_resolution = '%.0fkm'%self._display_resolution
            elif self._display_resolution >= 1:
                self._display_resolution = '%.1fkm'%self._display_resolution
            else:
                self._display_resolution = '%.2fkm'%self._display_resolution
            return self._display_resolution

        @property
        def center_lat_float(self):
            #Store everything internally as center lat/lon num lines/samples, pixel width/height
            # This is used int proj4_dict for pyresample AreaDefinition. Convert other options
            # to proj4_dict requirements
            if hasattr(self, 'center_lat'):
                self._center_lat_float = convert_lat_to_num(self.center_lat)
                return self._center_lat_float
            # Just check if hasattr min_lat, because if min_lat is defined min_lat_float will 
            # always be defined.  But will fail if you just check on min_lat_float and min_lat
            # isn't defined at all
            elif hasattr(self,'min_lat'):
                #log.info(minlon)
                self._center_lat_float = (self.min_lat_float + self.max_lat_float ) / 2
                return self._center_lat_float
            else:
                return None

        @property
        def center_lon_float(self):
            if not hasattr(self, '_center_lon_float'):
                if hasattr(self, 'center_lon'):
                    self._center_lon_float = convert_lon_to_num(self.center_lon)
                # Just check if hasattr min_lon, because if min_lon is defined min_lon_float will 
                # always be defined.  But will fail if you just check on min_lon_float and min_lon 
                # isn't defined at all.
                elif hasattr(self, 'min_lon'):
                    if self.max_lon_float < self.min_lon_float:
                        self._center_lon_float = (self.min_lon_float % 360) +\
                            ((self.max_lon_float % 360) -
                             (self.min_lon_float % 360)) / 2
                    else:
                        self._center_lon_float = self.min_lon_float +\
                                (self.max_lon_float - self.min_lon_float) / 2
                else:
                    self._center_lon_float = None
            return self._center_lon_float

        def lons_180_to_360(self):
            self._center_lon_float = convert_180_to_360(self.center_lon_float)
            self._min_lon_float = convert_180_to_360(self.min_lon_float)
            self._max_lon_float = convert_180_to_360(self.max_lon_float)

        #Projection stuff
        @property
        def long_projection(self): 
            self._long_projection = self.projection_info['longname'].lower()
            return self._long_projection
        @property
        def basemap_projection(self):
            self._basemap_projection = self.projection_info['name']
            return self._basemap_projection
        @property
        def proj4_projection(self):
            self._proj4_projection = self.projection_info['p4name']
            if self._proj4_projection is None:
                raise SectorFileError('Requested projection not available in Proj4.')
            return self._proj4_projection
        @property
        def projection_type(self):
            self._projection_type = self.projection_info['type']
            return self._projection_type
        @property
        def projection_info(self):
            self._projection_info = get_projection(self.node.xpath('projection')[0])
            return self._projection_info

    class Sources(object):
        def __init__(self, source_elements, scifile=None):
            # Initialize simple attributes
            self.node = source_elements
            self.scifile = scifile

        def testonly(self, sensorname, productname=None):
            testonly = False
            # If productname is not passed, just check sensor for testonly flag
            if not productname:
                if sensorname in self.sources_dict and \
                   'testonly' in self.sources_dict[sensorname] and \
                   str_to_bool(self.sources_dict[sensorname]['testonly']):
                    testonly = True
            # If productname is passed, check product for testonly flag
            else:
                if sensorname in self.products_dict and \
                   productname in self.products_dict[sensorname] and \
                   'testonly' in self.products_dict[sensorname][productname] and \
                   str_to_bool(self.products_dict[sensorname][productname]['testonly']):
                    testonly = True
            return testonly

        @property
        def sources_dict(self):
            if not hasattr(self, '_sources_dict'):
                self.get_source_dicts()
            return self._sources_dict

        @property
        def products_dict(self):
            if not hasattr(self, '_products_dict'):
                self.get_source_dicts()
            return self._products_dict

        def get_source_dicts(self):
            self._products_dict= {}
            self._sources_dict = {}
            for child in [self.node]+[xx for xx in self.node.itersiblings()]:
                if not child:
                    continue
                self._products_dict[child.values()[0]] = {}
                self._sources_dict[child.values()[0]] = {}
                for attr in child.items():
                    self._sources_dict[child.values()[0]][attr[0]] = attr[1]
                for child2 in child.iterchildren():
                    if child2.items():
                        self._products_dict[child.values()[0]][child2.values()[0]] = {}
                        for attr in child2.items()[1:]:
                            self._products_dict[child.values()[0]][child2.values()[0]][attr[0]] = attr[1]

    class SourceInfoNode(XMLNode):
        '''Class for handling the Source_Info element from a sectorfile.'''
        def __init__(self, source_node, scifile=None):
            super(Sector.SourceInfoNode, self).__init__(source_node)
            self._default = 'x'
            self.scifile = scifile
            self.__initialize = True

        @property
        def source_name_product(self):
            # Not settable via xml! Dynamically settable in reader. Used for filenames, merging, etc.
            # Default to scifile source_name_product - always set in
            # scifile, defaults to source name in scifile if not specified in reader.
            return self.scifile.source_name_product

        @property
        def platform_name_product(self):
            # Not settable via xml! Dynamically settable in reader. Used for filenames, merging, etc.
            # Default to scifile platform_name_product - always set in
            # scifile, defaults to platform name in scifile if not specified in reader.
            return self.scifile.platform_name_product

        @property
        def source_name_display(self):
            if self.eval_att('@source_name_display'):
                # source name to display on imagery - titles, legends, etc. Can be anything, never referenced 
                # internally to GeoIPS
                return self.eval_att('@source_name_display')
            else:
                # Default to scifile source_name_display - always set, defaults to source name if not 
                # specified in reader
                return self.scifile.source_name_display

        @property
        def platform_name_display(self):
            if self.eval_att('@platform_name_display'):
                # platform name to display on imagery - titles, legends, etc. Can be anything, never referenced 
                # internally to GeoIPS
                return self.eval_att('@platform_name_display')
            else:
                # Default to scifile platform_name_display - always set, defaults to platform name if not 
                # specified in reader
                return self.scifile.platform_name_display
            

    class TCInfoNode(XMLNode):
        '''Class for handling the TC_Info element from a sectorfile.'''
        def __init__(self, tc_node, scifile=None):
            super(Sector.TCInfoNode, self).__init__(tc_node)
            self._default = 'x'
            self.__initialize = True
            self.scifile = scifile

        @property
        def intensity(self):
            return self._intensity
        @intensity.setter
        def intensity(self,val):
            self._intensity = val 

        @property
        def wind_speed(self):
            return self._wind_speed
        @wind_speed.setter
        def wind_speed(self,val):
            self._wind_speed= val 

        @property
        def clat(self):
            return self._clat
        @clat.setter
        def clat(self,val):
            self._clat= val 

        @property
        def clon(self):
            return self._clon
        @clon.setter
        def clon(self,val):
            self._clon= val 

        @property
        def dtg(self):
            return self._dtg
        @dtg.setter
        def dtg(self,val):
            self._dtg= val 

        @property
        def storm_num(self):
            return self._storm_num
        @storm_num.setter
        def storm_num(self,val):
            self._storm_num= val 

        @property
        def storm_name(self):
            return self._storm_name
        @storm_name.setter
        def storm_name(self,val):
            self._storm_name= val 

    class PyroCBInfoNode(XMLNode):
        '''Class for handling the PyroCB_Info element from a sectorfile.'''
        def __init__(self, pyrocb_node,scifile=None):
            super(Sector.PyroCBInfoNode, self).__init__(pyrocb_node)
            self._default = 'x'
            self.__initialize = True
            self.scifile=scifile

        @property
        def min_lat(self):
            return self._minlat
        @min_lat.setter
        def min_lat(self,val):
            self._min_lat= val 

        @property
        def max_lat(self):
            return self._max_lat
        @max_lat.setter
        def max_lat(self,val):
            self._max_lat= val 

        @property
        def min_lon(self):
            return self._min_lon
        @min_lon.setter
        def min_lon(self,val):
            self._min_lon= val 

        @property
        def max_lon(self):
            return self._max_lon
        @max_lon.setter
        def max_lon(self,val):
            self._max_lon= val 

        @property
        def box_resolution_km(self):
            return self._box_resolution_km
        @box_resolution_km.setter
        def box_resolution_km(self,val):
            self._box_resolution_km= val 

    class PyroCBInfoNode(XMLNode):
        '''Class for handling the AtmosRiver_Info element from a sectorfile.'''
        def __init__(self, atmosriver_node,scifile=None):
            super(Sector.PyroCBInfoNode, self).__init__(atmosriver_node)
            self._default = 'x'
            self.__initialize = True
            self.scifile=scifile

        @property
        def min_lat(self):
            return self._minlat
        @min_lat.setter
        def min_lat(self,val):
            self._min_lat= val

        @property
        def max_lat(self):
            return self._max_lat
        @max_lat.setter
        def max_lat(self,val):
            self._max_lat= val

        @property
        def min_lon(self):
            return self._min_lon
        @min_lon.setter
        def min_lon(self,val):
            self._min_lon= val

        @property
        def max_lon(self):
            return self._max_lon
        @max_lon.setter
        def max_lon(self,val):
            self._max_lon= val

        @property
        def box_resolution_km(self):
            return self._box_resolution_km
        @box_resolution_km.setter
        def box_resolution_km(self,val):
            self._box_resolution_km= val

    class VolcanoInfoNode(XMLNode):
        '''Class for handling the Volcano_Info element from a sectorfile.'''
        def __init__(self, volcano_node,scifile=None):
            super(Sector.VolcanoInfoNode, self).__init__(volcano_node)
            self._default = 'x'
            self.__initialize = True
            self.scifile=scifile

        @property
        def summit_elevation(self):
            return self._summit_elevation
        @summit_elevation.setter
        def summit_elevation(self,val):
            self._summit_elevation= val 

        @property
        def plume_height(self):
            return self._plume_height
        @plume_height.setter
        def plume_height(self,val):
            self._plume_height= val 

        @property
        def wind_speed(self):
            return self._wind_speed
        @wind_speed.setter
        def wind_speed(self,val):
            self._wind_speed= val 

        @property
        def wind_dir(self):
            return self._wind_dir
        @wind_dir.setter
        def wind_dir(self,val):
            self._wind_dir= val 

        @property
        def clat(self):
            return self._clat
        @clat.setter
        def clat(self,val):
            self._clat= val 

        @property
        def clon(self):
            return self._clon
        @clon.setter
        def clon(self,val):
            self._clon= val 

    class NameNode(XMLNode):
        '''Class for handling the name element from a sectorfile.'''
        def __init__(self, name_node,scifile=None):
            super(Sector.NameNode, self).__init__(name_node)
            self._default = 'x'
            self.__initialize = True
            self.scifile=scifile

        @property
        def name_dict(self):
            self._name_dict = OrderedDict()
            name_parts = ['continent',
                          'country',
                          'area',
                          'subarea',
                          'state',
                          'city'
                         ]
            for part in name_parts:
                self._name_dict[part] = getattr(self, part) or self._default
            return self._name_dict

        @name_dict.setter
        def name_dict(self, new_dict):
	    #print "Setting name dict!!!"
            name_parts = ['continent',
                          'country',
                          'area',
                          'subarea',
                          'state',
                          'city'
                         ]
            for part in name_parts:
                setattr(self, part, new_dict[part])

        @property
        def region(self):
            self._region = "%s-%s-%s" % (self.continent, self.country or 'x', self.area or 'x')
            return self._region

        @property
        def subregion(self):
            self._subregion = "%s-%s-%s" % (self.subarea or 'x', self.state or 'x', self.city or 'x')
            return self._subregion

        @property
        def desig(self):
            self._desig = self.region+'-'+self.subregion
            return self._desig


    class PlotInfoNode(XMLNode):
        def __init__(self, plot_info_node, scifile=None):
            self.scifile=scifile
            super(Sector.PlotInfoNode, self).__init__(plot_info_node)

    class PlotObjectsNode(XMLNode):
        def __init__(self, objects_node,scifile=None):
            self.scifile=scifile
            super(Sector.PlotObjectsNode, self).__init__(objects_node,scifile=scifile)
        @property
        def objects(self):
            if not hasattr(self, '_objects'):
                self._objects = {}
                for node in self.node.iterchildren():
                    if node.tag == 'circle':
                        if not self._objects.has_key('circles'):
                            self.objects['circles'] = []
                        self._objects['circles'].append(self.Circle(node))
            return self._objects

        class Circle(XMLNode):
            def __init(self, circle_node, scifile=None):
                super(Sector.Circle, self).__init__(circle_node)


            @property
            def center_lat(self):
                if not hasattr(self, '_center_lat'):
                    self._center_lat = convert_lat_to_num(self.node.center_lat.pyval)
                return self._center_lat
            @center_lat.setter
            def center_lat(self, val):
                self._center_lat = val

            @property
            def center_lon(self):
                if not hasattr(self, '_center_lon'):
                    self._center_lon = convert_lon_to_num(self.node.center_lon.pyval)
                return self._center_lon
            @center_lon.setter
            def center_lon(self, val):
                self._center_lon = val

            @property
            def color(self):
                if not hasattr(self, '_color'):
                    try:
                        self._color = np.array([float(num) for num in self.node.color.pyval.strip().split()])/255.0
                    except ValueError:
                        self._color = self.node.color.pyval
                return self._color
            @color.setter
            def color(self, val):
                self._color = val

#######################################
# Getter and setter for boolean attributes in XML
#   get_bool_att
#   set_bool_att
# Properties for sector element attributes
#   name
#   time
#   isactive
#   isdynamic
#   download_on
#######################################
    def get_bool_att(self, name, path='.'):
        return get_bool_att(self, name, path)

    def set_bool_att(self, name, val, path='.'):
        val = bool_to_str(val)
        elem = self.node.xpath(path)[0]
        elem.set(name, val)

#Maybe want to make this automatically set to the modification time for
#   sectorfile.xml for non-dynamic sectors?  Will this be problematic?
    @property
    def dynamic_datetime(self):
        '''Getter method for sector's dynamic_datetime'''
        dynamic_datetime = self.node.xpath('@dynamic_datetime')[0]
        self._dynamic_datetime = datetime.strptime(dynamic_datetime,'%Y%m%d.%H%M%S') 
        return self._dynamic_datetime
    @dynamic_datetime.setter
    def dynamic_datetime(self, dt):
        '''Setter method for sector's dynamic_datetime'''
        dynamic_datetime = dt.strftime('%Y%m%d.%H%M%S')
        self.node.set('dynamic_datetime', dynamic_datetime)

    @property
    def dynamic_endtime(self):
        '''Getter method for sector's dynamic_endtime'''
        dynamic_endtime = self.node.xpath('@dynamic_endtime')[0]
        self._dynamic_endtime = datetime.strptime(dynamic_endtime,'%Y%m%d.%H%M%S') 
        return self._dynamic_endtime
    @dynamic_endtime.setter
    def dynamic_endtime(self, dt):
        '''Setter method for sector's dynamic_endtime'''
        dynamic_endtime = dt.strftime('%Y%m%d.%H%M%S')
        self.node.set('dynamic_endtime', dynamic_endtime)

    @property
    def isoperational(self):
        '''Determine whether sector is operational.  Returns a boolean.'''
        self._isoperational = self.get_bool_att('operational')
        return self._isoperational

    @isoperational.setter
    def isoperational(self, val):
        '''Sets whether a sector is operational or not.'''
        self.set_bool_att('operational', val)

    @property
    def isstitched(self):
        '''Determine whether sector should be stitched.  Returns a boolean.'''
        self._isstitched = self.get_bool_att('stitched')
        return self._isstitched

    @isstitched.setter
    def isstitched(self, val):
        '''Sets whether a sector should be stitched or not.'''
        self.set_bool_att('stitched', val)

    @property
    def isactive(self):
        '''Determine whether sector is active.  Returns a boolean.'''
        self._isactive = self.get_bool_att('active')
        return self._isactive

    @isactive.setter
    def isactive(self, val):
        '''Sets whether a sector is active or not.'''
        self.set_bool_att('active', val)

    @property
    def testonly(self):
        '''Determine whether sector is testonly.  Returns a boolean.'''
        self._testonly = self.get_bool_att('testonly')
        return self._testonly

    @testonly.setter
    def testonly(self, val):
        '''Set testonly attribute of destinations element to "yes" for the current sector.'''
        self.set_bool_att('testonly', val)


    @property
    def isdynamic(self):
        '''Determine whether sector is for determining download of granules.  Returns a boolean.'''
        self._isdynamic = self.get_bool_att('dynamic')
        return self._isdynamic
    @isdynamic.setter
    def isdynamic(self, val):
        '''Sets whether a sector is dynamic or not.'''
        self.set_bool_att('dynamic', val)

    @property
    def download_on(self):
        '''Determine whether sector is for determining download of granules.  Returns a boolean.'''
        self._download_on = self.get_bool_att('download')
        return self._download_on
    @download_on.setter
    def download_on(self, val):
        '''Sets whether to download data for a sector or not.'''
        self.set_bool_att('download', val)

    @property
    def composite_on(self):
        '''Determine whether sector imagery should be composited for polar sensors.  Returns a boolean.'''
        self._composite_on = self.get_bool_att('composite')
        return self._composite_on
    @composite_on.setter
    def composite_on(self, val):
        '''Setse whether to composite polar swaths for a sector or not.'''
        self.set_bool_att('composite', val)

#######################################
# Getter and setter for boolean attributes in destinations element
#   get_destination_att
#   set_destination_att
# Properties for destinations element attributes
#   public_on
#   private_on
#   tc_on
#   atcf_on
#   tropical_on
#   test_on
# Function for all Destinations
#   destinations
#######################################
    def get_destinations_att(self, dest):
        '''Determine whether a specific destination is turned on or off for the current sector.'''
        onoff = self.get_bool_att(dest, 'destinations')
        return onoff
    def set_destinations_att(self, dest, val):
        '''Sets whether imagery for the current sector should be sent to a specific destination.'''
        self.set_bool_att(dest, val, 'destinations')
    
    @property
    def public_on(self):
        '''Determine whether sector is for public page.  Returns a boolean.'''
        self._public_on = self.get_destinations_att('public')
        return self._public_on
    @public_on.setter
    def public_on(self, val):
        '''Set public attribute of destinations element to "yes" for the current sector.'''
        self.set_destinations_att('public', val)

    @property
    def pyrocb_on(self):
        '''Determine whether sector is for pyrocb page.  Returns a boolean.'''
        self._pyrocb_on = self.get_destinations_att('pyrocb')
        return self._pyrocb_on
    @pyrocb_on.setter
    def pyrocb_on(self, val):
        '''Set pyrocb attribute of destinations element to "yes" for the current sector.'''
        self.set_destinations_att('pyrocb', val)

    @property
    def atmosriver_on(self):
        '''Determine whether sector is for atmosriver page.  Returns a boolean.'''
        self._atmosriver_on = self.get_destinations_att('atmosriver')
        return self._atmosriver_on
    @atmosriver_on.setter
    def atmosriver_on(self, val):
        '''Set atmosriver attribute of destinations element to "yes" for the current sector.'''
        self.set_destinations_att('atmosriver', val)

    @property
    def atcf_on(self):
        '''Determine whether sector is for atcf page.  Returns a boolean.'''
        self._atcf_on = self.get_destinations_att('atcf')
        return self._atcf_on
    @atcf_on.setter
    def atcf_on(self, val):
        '''Set atcf attribute of destinations element to "yes" for the current sector.'''
        self.set_destinations_att('atcf', val)

    @property
    def private_on(self):
        '''Determine whether sector is for private page.  Returns a boolean.'''
        self._private_on = self.get_destinations_att('private')
        return self._private_on
    @private_on.setter
    def private_on(self, val):
        '''Set private attribute of destinations element to "yes" for the current sector.'''
        self.set_destinations_att('private', val)

    @property
    def tropical_on(self):
        '''Determine whether sector is for tropical page.  Returns a boolean.'''
        self._tropical_on = self.get_destinations_att('tropical')
        return self._tropical_on
    @tropical_on.setter
    def tropical_on(self, val):
        '''Set tropical attribute of destinations element to "yes" for the current sector.'''
        self.set_destinations_att('tropical', val)

    @property
    def datanrl_on(self):
        '''Determine whether data needs to go to NRL.  Returns a boolean.'''
        self._datanrl_on = self.get_destinations_att('datanrl')
        return self._datanrl_on
    @datanrl_on.setter
    def datanrl_on(self, val):
        '''Set datanrl attribute of destinations element to "yes" for the current sector.'''
        self.set_destinations_att('datanrl', val)

    @property
    def archive_on(self):
        '''Determine whether sector is for archive page.  Returns a boolean.'''
        self._archive_on = self.get_destinations_att('archive')
        return self._archive_on
    @archive_on.setter
    def archive_on(self, val):
        '''Set archive attribute of destinations element to "yes" for the current sector.'''
        self.set_destinations_att('archive', val)

    @property
    def tc_on(self):
        '''Determine whether sector is tc.  Returns a boolean.'''
        self._tc_on = self.get_destinations_att('tc')
        return self._tc_on
    @tc_on.setter
    def tc_on(self, val):
        '''Set tc attribute of destinations element to "yes" for the current sector.'''
        self.set_destinations_att('tc', val)

    @property
    def metoctiff_on(self):
        '''Determine whether sector is metoctiff.  Returns a boolean.'''
        self._metoctiff_on = self.get_destinations_att('metoctiff')
        return self._metoctiff_on
    @metoctiff_on.setter
    def metoctiff_on(self, val):
        '''Set metoctiff attribute of destinations element to "yes" for the current sector.'''
        self.set_destinations_att('metoctiff', val)

    @property
    def test_on(self):
        '''Determine whether sector is test.  Returns a boolean.'''
        self._test_on = self.get_destinations_att('test')
        return self._test_on
    @test_on.setter
    def test_on(self, val):
        '''Set test attribute of destinations element to "yes" for the current sector.'''
        self.set_destinations_att('test', val)

    @property
    def any_public(self):
        if self.public_on or self.tropical_on or self.tc_on or self.atcf_on or self.pyrocb_on or self.atmosriver_on:
            return True
        else:
            return False

    def turn_public_off(self):
        for attr in ['public_on', 'tropical_on', 'tc_on','atcf_on','pyrocb_off','atmosriver_off']:
            setattr(self, attr, False)

    @property
    def  destinations_dict(self):
        self._destinations_dict = OrderedDict()
        dest_parts = ['public',
                      'private',
                      'pyrocb',
                      'atmosriver',
                      'tropical',
                      'datanrl',
                      'tc',
                      'atcf',
                      'metoctiff',
                      'test',
                      'archive',
                     ]
        for part in dest_parts:
            self._destinations_dict[part] = getattr(self, part+"_on")
        return self._destinations_dict

    @destinations_dict.setter
    def destinations_dict(self, new_dict):
        #print "Setting destinations!!!!"
        dest_parts = ['public',
                        'private',
                        'pyrocb',
                        'atmosriver',
                        'tropical',
                        'datanrl',
                        'tc',
                        'atcf',
                        'metoctiff',
                        'test',
                        'archive',
                       ]
        for part in dest_parts:
            setattr(self, part, new_dict[part])



    @property
    def private_link(self):
        self._private_link = self.node.xpath('private_link')
        if self._private_link:
            self._private_link = os.getenv('SATFOCUS')+'/'+self._private_link[0]
        return self._private_link
    @property
    def public_link(self):
        self._public_link = self.node.xpath('public_link')
        if self._public_link:
            self._public_link = os.getenv('SATFOCUS')+'/'+self._public_link[0]
        return self._public_link
    @property
    def tropical_link(self):
        self._tropical_link = self.node.xpath('tropical_link')
        if self._tropical_link:
            self._tropical_link = os.getenv('SATFOCUS')+'/'+self._tropical_link[0]
        return self._tropical_link
    @property
    def archive_link(self):
        self._archive_link = self.node.xpath('archive_link')
        if self._archive_link:
            self._archive_link = os.getenv('SATFOCUS')+'/'+self._archive_link[0]
        return self._archive_link
    @property
    def tc_link(self):
        self._tc_link = self.node.xpath('tc_link')
        if self._tc_link:
            self._tc_link = os.getenv('SATFOCUS')+'/'+self._tc_link[0]
        return self._tc_link
    @property
    def metoctiff_link(self):
        self._metoctiff_link = self.node.xpath('metoctiff_link')
        if self._metoctiff_link:
            self._metoctiff_link = os.getenv('SATFOCUS')+'/'+self._metoctiff_link[0]
        return self._metoctiff_link

#    def set_destinations(self):
#        for key, val in self.node.destinations.attrib.items():
#            setattr(self, key+'_on', val)

#######################################
# Path operations
#######################################
    @property
    def path(self):
        self._path = self.getpath(self.node)
        return self._path

    @property
    def roottree(self):
        self._roottree = self.node.getroottree()
        return self._roottree

    def getpath(self, element):
        rt = self.roottree
        path = rt.getpath(element)
        return path



def get_bool_att(obj, name, path='.'):
    val = obj.node.xpath('%s/@%s' % (path, name))[0]
    try:
        onoff = str_to_bool(val)
    except ValueError:
        raise SFAttributeError('%s/@%s attribute for %s sector must be either yes or no' 
                               % (path, name, obj.name))
    return onoff

def str_to_bool(val, yes='yes', no='no'):
    '''Converts a "boolean" string to a boolean.
    If val equals the value of yes, then return True.
    If val equals the value of no, then return False.
    If val equals neither the value of yes or no, raise a ValueError.
    Arguments:
        val - String to convert to boolean
    Keywords:
        yes - Value to use as True
        no  - Value to use as False
    '''
    #If val is already a boolean return it now
    if val is True or val is False:
        return val
    #Test val and return appropriate boolean
    if val.lower() == yes.lower():
        return True
    elif val.lower() == no.lower():
        return False
    else:
        raise ValueError('Value must be str(%s) or str(%s).  Got %r.' % (yes, no, val))

def bool_to_str(val, yes='yes', no='no'):
    '''Converts a boolean to a "boolean" string.
    If val is True then return the value of yes.
    If val is False then return the value of no.
    If val is neither True nor False then raise a ValueError.
    Arguments:
        val - A boolean
    Keywords:
        yes - Value to use as True
        no  - Value to use as False
    '''
    #If val already equals either yes or no return it now
    if val == yes or val == no:
        return val
    if val is True:
        return yes
    elif val is False:
        return no
    else:
        raise ValueError('Value must be True or False.  Got %r.' % (yes, no, val)) 
