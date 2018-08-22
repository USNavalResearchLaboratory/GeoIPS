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
import re
from collections import OrderedDict
import logging

# Installed Libraries
from lxml import etree


# GeoIPS Libraries
from .ProductFileError import *
from geoips.utils.xml_utilities import read_xmlfile


log = logging.getLogger(__name__)

class XMLProductFile(object):
    def __init__(self, productfile, scifile=None):
        if not os.path.isfile(productfile):
            raise IOError('Input path is not a regular file.  Got %s.' % productfile)
        self.name = productfile
        self.tree = read_xmlfile(self.name, do_objectify=True)
        self.scifile = scifile
        self.root = self.tree.getroot()

    def __repr__(self):
        return "productfile.%s(%r)" % (self.__class__.__name__, self.name)

    def reset(self):
        '''Resets the object to its previous state.'''

    #Used when the object has been modified to indicate that the object should re-read properties
    def __set_dirty(self):
        self._dirty = True
    def __set_clean(self):
        self._dirty = False
    @property
    def dirty(self):
        if not hasattr(self, '_dirty'):
            self._dirty = True
        return self._dirty
    def when_dirty(self):
        '''Make sure all properties get updated appropriately.'''
        del self._sources

    def productnames(self):
        '''Returns a list of all product names in the current object.'''
        return self.root.xpath('product/@name')

    @property
    def sources(self):
        if not hasattr(self, '_sources'):
            for prod in self.iterproducts():
                self._sources = {}
                for source_name, source in prod.sources.items():
                    if not sources.has_key(source_name):
                        self._sources[source_name] = source
                    else:
                        self._sources[source_name] = sources[source_name].merge(source)
        return self._sources

    # This is ONLY used for multisource methods.  It is it's own separate thing, handled 
    # differently than all the other product types. Does not process any data - just 
    # takes existing products and sticks them together using some sort of logic, found
    # in geoimg.
    @property
    def productlayers(self):
        if not hasattr(self, '_productlayers'):
            for prod in self.iterproducts():
                self._productlayers = {}
                for productlayer_name, productlayer in prod.productlayers.items():
                    if not productlayers.has_key(productlayer_name):
                        self._productlayers[productlayer_name] = productlayer
                    else:
                        self._productlayers[productlayer_name] = productlayers[productlayer_name].merge(productlayer)
        return self._productlayers


    def get_required_source_vars(self, source):
        '''Returns a list containing the names of the variables required for the current set of products
        for the provided data source name.'''
        variables = set()
        for prod in self.iterproducts(source):
            variables.update(set(prod.get_required_source_vars(source)))
        return list(variables)

    def get_optional_source_vars(self, source):
        '''Returns a list containing the names of the variables required for the current set of products
        for the provided data source name.'''
        variables = set()
        for prod in self.iterproducts(source):
            variables.update(set(prod.get_optional_source_vars(source)))
        return list(variables)

    def get_required_source_geolocation_vars(self, source):
        '''Returns a list containing the names of the variables required for the current set of products
        for the provided data source name.'''
        variables = set()
        for prod in self.iterproducts(source):
            variables.update(set(prod.get_required_source_geolocation_vars(source)))
        return list(variables)

    def getproducts(self, source=None):
        '''Returns a list of all contained products'''
        prods = []
        prods = [Product(prod, scifile=self.scifile) for prod in self.root.xpath('product')]
        return prods

    def iterproducts(self, source=None):
        '''Iterates over all product elements in the current object for a given source.'''
        ind = 1
        while True:
            try:
                #Grab the element at position "ind"
                element = self.root.xpath('product[%r]' % ind)[0]
                ind += 1
                prod = Product(element, scifile=self.scifile)
                if source is not None and source not in prod.sources:
                    continue
                else:
                    yield Product(element, scifile=self.scifile)
            except IndexError:
                break

    @property
    def dataset_names(self):
        '''Returns a list of datasets required for the given set of products.'''
        if self.dirty:
            self._dataset_names = set()
            for prod in self.iterproducts():
                self._dataset_names.union_update(prod.dataset_names)
        return list(self._dataset_names)

    def open_product(self, name):
        '''Instantiates a Product object by short name.'''
        #try:
        #    element = self.root.xpath('product[@name="%s"]' % name)[0]
        #except IndexError:
        #    return None
        elements = self.root.xpath('product')
        for element in elements:
            if element.attrib['name'].lower() == name.lower():
                return Product(element, scifile=self.scifile)
        #If no product found, return None
        return None

    def join(self, other):
        '''Joins two product files together into a single product file.'''
        products_other = other.getproducts()
        product_nodes = [prod.node for prod in products_other]
        self.extend(product_nodes)
        self.__set_dirty()

    def append(self, element):
        '''Appends a new product element to the end of the root element.'''
        try:
            element = element.node
        except AttributeError:
            pass
        if element.tag == 'product' and element.attrib['name'] not in self.productnames():
            self.root.append(element)
            self.__set_dirty()
            #self.append_names.append(element.attrib['name'])
        elif element.attrib['name'] in self.productnames():
            raise ProductFileError('Duplicate product name encountered: '+str(element.attrib['name']))
        else:
            raise ProductFileError('''Can only append product elements to root element.
                                   Given %s element.''' % element.tag)

    def extend(self, element_list):
        '''Appends a list of product elements to the end of the root element.'''
        for element in element_list:
            self.append(element)
        self.__set_dirty()

    def remove(self, name):
        '''Removes a product from the current object.  Product is found
        by its "name" attribute.'''
        element = self.root.xpath('product[@name="%s"]' % name)
        try:
            self.root.remove(element[0])
            self.__set_dirty()
        except ValueError:
            log.warning('Cannot remove product named %s.  Does not exist.'  % name)

class Product(object):
    def __init__(self, product_xml, scifile=None):
        self.node = product_xml
        self.scifile = scifile
        #self.min_cover = 40

    def __str__(self):
        return etree.tostring(self.node, pretty_print=True)

    def eval_str(self,val):
        try:
            return eval(val)
        except:
            return val

    def eval_att(self,path):
        return self.eval_str(self.node.xpath(path)[0])

    @property
    def name(self):
        if not hasattr(self, '_name'):
            self._name = self.node.attrib['name']
        return self._name

    @property
    def product_name_display(self):
        if self.eval_att('@display_name'):
            # display_name used for titles, legends, etc. Product always referenced within GeoIPS as "name"
            return self.eval_att('@display_name')
        else:
            # Default to product "name" if display_name not specified.
            return self.name

    def get_required_source_vars(self, source):
        '''Return a list containing the names of the variables required for the current product
        for the given data source name.'''
        return [xx.name for xx in self.sources[source].variables.values() if not xx.optional]

    def get_optional_source_vars(self, source):
        '''Return a list containing the names of the variables required for the current product
        for the given data source name.'''
        return [xx.name for xx in self.sources[source].variables.values() if xx.optional]

    def get_required_source_geolocation_vars(self, source):
        '''Return a list containing the names of the geolocation variables required for the current product
        for the given data source name.'''
        # Add SunZenith if day_ngt is not both
        gvars = []
        if self.sources[source].product.day_ngt != 'both':
            gvars = ['SunZenith']
        return gvars + self.sources[source].geolocation_variables.keys()

    @property
    def method(self):
        if not hasattr(self, '_method'):
            self._method = self.node.attrib['method']
        return self._method

    @property
    def finalonly(self):
        if not hasattr(self, '_finalonly'):
            self._finalonly = test_attrib_bool(self.node, 'finalonly')
        return self._finalonly
    @finalonly.setter
    def finalonly(self, val):
        self._finalonly = val

    @property
    def granule_composites(self):
        if not hasattr(self, '_granule_composites'):
            self._granule_composites = test_attrib_bool(self.node, 'granule_composites')
        return self._granule_composites
    @granule_composites.setter
    def granule_composites(self, val):
        self._granule_composites= val

    @property
    def testonly(self):
        if not hasattr(self, '_testonly'):
            self._testonly = test_attrib_bool(self.node, 'testonly')
        return self._testonly
    @testonly.setter
    def testonly(self, val):
        self._testonly = val

    @property
    def plot_method(self):
        if not hasattr(self, '_plot_method'):
            try:
                self._plot_method = 'plot_%s' % self.node.attrib['plotmethod']
            except KeyError:
                self._plot_method = 'plot_%' % self.method
        return self._plot_method

    @property
    def sources(self):
        '''
        A dictionary whose keys are the names of the required data sources and whose keys
        are productfile.Source instances.
        '''
        if not hasattr(self, '_sources'):
            self._sources = {}
            for source_elem in self.node.iterfind('./%s_args/source' % self.method):
                source = Source(self, source_elem, scifile=self.scifile)
                if not self._sources.has_key(source.name):
                    self._sources[source.name] = source
                else:
                    raise ProductFileError('Duplicate Source name encountered.')
        return self._sources

    # This is ONLY used for multisource methods.  It is it's own separate thing, handled 
    # differently than all the other product types. Does not process any data - just 
    # takes existing products and sticks them together using some sort of logic, found
    # in geoimg.
    @property
    def productlayers(self):
        '''
        A dictionary whose keys are the names of the required data sources and whose keys
        are productfile.Source instances.
        '''
        if not hasattr(self, '_productlayers'):
            self._productlayers = {}
            for productlayer_elem in self.node.iterfind('./%s_args/productlayer' % self.method):
                productlayer = Productlayer(self, productlayer_elem, scifile=self.scifile)
                if not self._productlayers.has_key(productlayer.name):
                    self._productlayers[productlayer.name] = productlayer
                else:
                    raise ProductFileError('Duplicate Productlayer name encountered.')
        return self._productlayers

    @property
    def datasets(self):
        '''A list of datasets needed for this product.'''
        if not hasattr(self, '_datasets'):
            self._datasets = {}
            for ds_elem in self.node.iterfind('./%s_args/datasets' % self.method):
                dataset = Dataset(ds_elem, scifile=self.scifile)
                if not self._datasets.has_key(dataset.name):
                    self._datasets[dataset.name] = dataset
                else:
                    raise ProductFileError('Duplicate Dataset name encountered.')
        return self._dataset_list

    @property
    def product_args(self):
        if not hasattr(self, '_product_args'):
            method = self.method
            self._product_args = self.node.find(method.lower()+'_args')
        return self._product_args

    @property
    def images(self):
        if not hasattr(self, '_images'):
            self._images = {}
            for child in self.product_args.iterchildren():
                if child.find('equation') is not None:
                    self._images[child.tag] = Image(self, child)
        return self._images

    @property
    def beamwidth(self):
        if not hasattr(self, '_beamwidth'):
            #What happens here when there is no beamwidth node?
            self._beamwidth = self.product_args.find('beamwidth')
            try:
                self._beamwidth = self._beamwidth.pyval
            except AttributeError:
                self._beamwidth = None
        return self._beamwidth

    @property
    def min_cover(self):
        if not hasattr(self, '_min_cover'):
            #What happens here when there is no day_ngt node?
            self._min_cover = self.product_args.find('min_cover')
            try:
                self._min_cover = self._min_cover.pyval
            except AttributeError:
                self._min_cover = None
        return self._min_cover

    @property
    def interpmethod(self):
        if not hasattr(self, '_interpmethod'):
            #What happens here when there is no day_ngt node?
            self._interpmethod = self.product_args.find('interpmethod')
            try:
                self._interpmethod = self._interpmethod.pyval
            except AttributeError:
                self._interpmethod = None
        return self._interpmethod

    @property
    def day_ngt(self):
        if not hasattr(self, '_day_ngt'):
            #What happens here when there is no day_ngt node?
            self._day_ngt = self.product_args.find('day_night')
            try:
                self._day_ngt = self._day_ngt.pyval
            except AttributeError:
                self._day_ngt = 'both'
        return self._day_ngt

    @property
    def day_ang(self):
        if not hasattr(self, '_day_ang'):
            self._day_ang = self.product_args.find('max_day_zen_ang')
            try:
                self._day_ang = self._day_ang.pyval
            except AttributeError:
                self._day_ang = 90
        return self._day_ang

    @property
    def ngt_ang(self):
        if not hasattr(self, '_ngt_ang'):
            self._ngt_ang = self.product_args.find('min_ngt_zen_ang')
            try:
                self._ngt_ang = self._ngt_ang.pyval
            except AttributeError:
                self._ngt_ang = 90
        return self._ngt_ang

    @property
    def colorbars(self):
        if not hasattr(self, '_colorbars'):
            cbnodes = self.product_args.findall('colorbar')
            self._colorbars = []
            for cbnode in cbnodes:
                self._colorbars.append(Colorbar(cbnode, scifile=self.scifile))
        return self._colorbars

    @property
    def text_below_colorbars(self):
        if not hasattr(self, '_text_below_colorbars'):
            legend_text = self.product_args.find('legend_text')
            if legend_text:
                try:
                    textstr = legend_text.find('below_colorbars').pyval.strip().decode('string_escape')
                except AttributeError:
                    textstr = None
            else:
                textstr = None
            self._text_below_colorbars = self.eval_str(textstr)
        return self._text_below_colorbars
    @property
    def text_above_colorbars(self):
        if not hasattr(self, '_text_above_colorbars'):
            legend_text = self.product_args.find('legend_text')
            if legend_text:
                try:
                    textstr = legend_text.find('above_colorbars').pyval.strip().decode('string_escape')
                except AttributeError:
                    textstr = None
            else:
                textstr = None
            self._text_above_colorbars = self.eval_str(textstr)
        return self._text_above_colorbars
    @property
    def text_below_title(self):
        if not hasattr(self, '_text_below_title'):
            legend_text = self.product_args.find('legend_text')
            if legend_text:
                try:
                    textstr = legend_text.find('below_title').pyval.strip().decode('string_escape')
                except AttributeError:
                    textstr = None
            else:
                textstr = None
            self._text_below_title = self.eval_str(textstr)
        return self._text_below_title

    @property
    def cmap(self):
        if not hasattr(self, '_cmap'):
            self._cmap = self.product_args.find('cmap')
            if not self._cmap:
                self._cmap = None
        return self._cmap

    @property
    def interpolation(self):
        if not hasattr(self, '_interpolation'):
            self._interpolation = self.product_args.find('interpolation')
        return self._interpolation

    @property
    def interpolation_radius_of_influence(self):
        if not hasattr(self, '_interpolation_radius_of_influence'):
            self._interpolation_radius_of_influence = self.product_args.find('interpolation_radius_of_influence')
            if self._interpolation_radius_of_influence:
                self._interpolation_radius_of_influence = float(self._interpolation_radius_of_influence)
        return self._interpolation_radius_of_influence

    @property
    def gridcolor(self):
        if not hasattr(self, '_gridcolor'):
            try:
                self._gridcolor = self.product_args.find('gridcolor').pyval
            except AttributeError:
                self._gridcolor = '0.0 0.0 0.0'
            try:
                self._gridcolor = [float(elem) for elem in self._gridcolor.split()]
            except AttributeError:
                raise ProductFileError('Element "gridcolor" must contain an RGB tripple')
            if not self._gridcolor:
                self._gridcolor = [0.0,0.0,0.0]
        return self._gridcolor

    @property
    def coastcolor(self):
        if not hasattr(self, '_coastcolor'):
            try:
                self._coastcolor = self.product_args.find('coastcolor').pyval
            except AttributeError:
                self._coastcolor = '0.0 0.0 0.0'
            try:
                self._coastcolor = [float(elem) for elem in self._coastcolor.split()]
            except AttributeError:
                raise ProductFileError('Element "coastcolor" must contain an RGB tripple')
            if not self._coastcolor:
                self._coastcolor = [0.0,0.0,0.0]
        return self._coastcolor


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

class Image(object):
    def __init__(self, product, image_xml=None):
        self.product = product
        self.node = image_xml

    @property
    def name(self):
        if not hasattr(self, '_name'):
            self._name = self.node.tag
        return self._name

    @property
    def required_variables(self):
        full_eq = ' '.join(self.equations.values())
        self._required_variables = {}
        for source in self.product.sources.values():
            for var_name, var in source.variables.items():
                if var_name.lower() in full_eq.lower():
                    if not self._required_variables.has_key(source):
                        self._required_variables[source] = []
                    self._required_variables[source].append(var_name)
        return self._required_variables

    @property
    def required_geolocation_variables(self):
        full_eq = ' '.join(self.equations.values())
        self._required_geolocation_variables = {}
        for source in self.product.sources.values():
            for var_name, var in source.geolocation_variables.items():
                if var_name.lower() in full_eq.lower():
                    if not self._required_geolocation_variables.has_key(source):
                        self._required_geolocation_variables[source] = []
                    self._required_geolocation_variables[source].append(var_name)
        return self._required_geolocation_variables

    @property
    def equations(self):
        if not hasattr(self, '_equations'):
            self._equations = OrderedDict()
            for eq in self.node.findall('equation'):
                eq_name = eq.attrib['eq_name']
                if self._equations.has_key(eq_name):
                    raise ProductFileError('Duplicate equation name encountered.')
                self._equations[eq_name] = eq.pyval
            if len(self._equations.keys()) > 1 and '' in self._equations.keys():
                raise ProductFileError('''Equation names must not be set to 
                                       the null string when multiple equations are present.''')
            joined_names = ' '.join(self._equations.keys())
            for eq_name in self._equations.keys():
                if len(re.findall(eq_name, joined_names)) > 1:
                    raise ProductFileError('''Equation names must be unique and cannot be contained in other equation names\n
                                           For example, "red" and "red" cannot both be used.
                                           More importantly, "red" and "red2" cannot both be used.
                                           Using "red1" and "red2" is permissable.''')
        return self._equations

    @property
    def range(self):
        if not hasattr(self, '_range'):
            self._range = {}
            for elem in self.node.find('range').iterchildren():
                self._range[elem.tag.lower()] = elem.pyval if (elem.pyval or elem.pyval == 0) else None
        return self._range

    @property
    def min(self):
        if not hasattr(self, '_min'):
            self._min = self.range['min_value']
        return self._min

    @property
    def max(self):
        if not hasattr(self, '_max'):
            self._max = self.range['max_value']
        return self._max

    @property
    def min_outbounds(self):
        ''' Default to 'crop', unless specified in productfile xml'''
        if not hasattr(self, '_min_outbounds'):
            try:
                self._min_outbounds = self.range['min_outbounds']
            except KeyError:
                try:
                    self._min_outbounds = self.range['outbounds']
                except KeyError:
                    self._min_outbounds = 'crop'
        return self._min_outbounds

    @property
    def max_outbounds(self):
        ''' Default to 'crop', unless specified in productfile xml'''
        if not hasattr(self, '_max_outbounds'):
            try:
                self._max_outbounds = self.range['max_outbounds']
            except KeyError:
                try:
                    self._max_outbounds = self.range['outbounds']
                except KeyError:
                    self._max_outbounds = 'crop'
        return self._max_outbounds

    @property
    def units(self):
        if not hasattr(self, '_units'):
            self._units = self.range['units']
        return self._units

    @property
    def inverse(self):
        ''' Default to False, unless specified in productfile xml'''
        if not hasattr(self, '_inverse'):
            if 'inverse' in self.range.keys() and self.range['inverse'] == 'yes':
                self._inverse = True
            else:
                self._inverse = False
        return self._inverse

    @property
    def normalize(self):
        ''' Default to True, unless specified in productfile xml'''
        if not hasattr(self, '_normalize'):
            if 'normalize' in self.range.keys() and self.range['normalize'] == 'no':
                self._normalize = False
            else:
                self._normalize = True
        return self._normalize

    @property
    def color(self):
        if not hasattr(self, '_color'):
            self._color = None
            color = self.node.find('color')
            if color:
                self._color = color
        return self._color

    @property
    def best_possible_pixel_width(self):
        if not hasattr(self, '_best_possible_pixel_width'):
            self._best_possible_pixel_width = None
            best_possible_pixel_width = self.node.find('best_possible_pixel_width')
            if best_possible_pixel_width:
                self._best_possible_pixel_width = best_possible_pixel_width
        return self._best_possible_pixel_width

    @property
    def best_possible_pixel_height(self):
        if not hasattr(self, '_best_possible_pixel_height'):
            self._best_possible_pixel_height = None
            best_possible_pixel_height = self.node.find('best_possible_pixel_height')
            if best_possible_pixel_height:
                self._best_possible_pixel_height = best_possible_pixel_height_
        return self._best_possible_pixel_height

    @property
    def gamma(self):
        if not hasattr(self, '_gamma'):
            self._gamma = None
            gamma1 = self.node.find('gamma1')
            gamma2 = self.node.find('gamma2')
            if gamma1:
                self._gamma = [gamma1.pyval]
                if gamma2:
                    self._gamma.append(gamma2.pyval)
            elif gamma2:
                log.warning('Gamma2 set without Gamma1.  Ignoring Gamma2.')
        return self._gamma

# This is ONLY used for multisource methods.  It is it's own separate thing, handled 
# differently than all the other product types. Does not process any data - just 
# takes existing products and sticks them together using some sort of logic, found
# in geoimg.
# Copied and pasted analog from "source" (for "normal" data processing product files)
class Productlayer(object):
    def __init__(self, product, source_xml=None, scifile=None):
        self.product = product
        self.node = source_xml
        self.scifile = scifile

    def __str__(self):
        return etree.tostring(self.node, pretty_print=True)

    @property
    def name(self):
        if not hasattr(self, '_name'):
            self._name = self.node.attrib['name']
        return self._name

    @property
    def order(self):
        if not hasattr(self, '_order'):
            self._order = self.node.attrib['order']
        return self._order

    @property
    def hour_range(self):
        try:
            if not hasattr(self, '_hour_range'):
                self._hour_range = int(self.node.attrib['hour_range'])
        except ValueError:
            self._hour_range = 2 
        return self._hour_range

    @property
    def matchall(self):
        if not hasattr(self, '_matchall'):
            self._matchall = False
            if self.node.attrib['matchall'] == 'yes':
                self._matchall = True
        return self._matchall

    @property
    def runonreceipt(self):
        if not hasattr(self, '_runonreceipt'):
            self._runonreceipt = self.node.attrib['runonreceipt']
        return self._runonreceipt

    @property
    def possiblesources(self):
        if not hasattr(self, '_possiblesources'):
            self._possiblesources = {}
            for src_elem in self.node.iterfind('.//possiblesource'):
                src = Possiblesource(self.product, self, src_elem, scifile=self.scifile)
                if not self._possiblesources.has_key(src.name):
                    self._possiblesources[src.name] = src
                else:
                    raise ProductFileError('Duplicate Possiblesource name encountered in single Possiblesource. '+str(self.product.name))
        return self._possiblesources


    def merge(self, other):
        if not self.name == other.name:
            raise ProductFileError('Cannot merge Productlayer instances for different sources.')
        new = _Productlayer()
        new._name = self.name
        new._possiblesources= {}
        new._possiblesources.update(self)
        new._possiblesources.update(other)
        return new


# This is ONLY used for multisource methods.  It is it's own separate thing, handled 
# differently than all the other product types. Does not process any data - just 
# takes existing products and sticks them together using some sort of logic, found
# in geoimg.
# Copied and pasted analog from "source" (for "normal" data processing product files)
class _Productlayer(Productlayer):
    def __init__(self):
        self.product = None
        self.node = None
        self._name = None
        self._possiblesources = None

class Source(object):
    def __init__(self, product, source_xml=None, scifile=None):
        self.product = product
        self.node = source_xml
        self.scifile = scifile

    def __str__(self):
        return etree.tostring(self.node, pretty_print=True)

    @property
    def name(self):
        if not hasattr(self, '_name'):
            self._name = self.node.attrib['name']
        return self._name

    @property
    def granule_composites(self):
        if not hasattr(self, '_granule_composites'):
            self._granule_composites = test_attrib_bool(self.node, 'granule_composites')
        return self._granule_composites

    @property
    def variables(self):
        if not hasattr(self, '_variables'):
            self._variables = {}
            for var_elem in self.node.iterfind('.//var'):
                var = Variable(self.product, self, var_elem, scifile=self.scifile)
                if not self._variables.has_key(var.name):
                    self._variables[var.name] = var
                else:
                    raise ProductFileError('Duplicate Variable name encountered in single Source. '+str(self.product.name))
        return self._variables

    @property
    def geolocation_variables(self):
        if not hasattr(self, '_geolocation_variables'):
            self._geolocation_variables = {}
            for var_elem in self.node.iterfind('.//gvar'):
                var = Variable(self.product, self, var_elem, scifile=self.scifile)
                if not self._geolocation_variables.has_key(var.name):
                    self._geolocation_variables[var.name] = var
                else:
                    raise ProductFileError('Duplicate Variable name encountered in single Source.')
        return self._geolocation_variables

    def merge(self, other):
        if not self.name == other.name:
            raise ProductFileError('Cannot merge Source instances for different sources.')
        new = _Source()
        new._name = self.name
        new._variables = {}
        new._variables.update(self)
        new._variables.update(other)
        return new

class _Source(Source):
    def __init__(self):
        self.product = None
        self.node = None
        self._name = None
        self._variables = None

# This is ONLY used for multisource methods.  It is it's own separate thing, handled 
# differently than all the other product types. Does not process any data - just 
# takes existing products and sticks them together using some sort of logic, found
# in geoimg.
# Copied and pasted analog from "var" (for "normal" data processing product files)
class Possiblesource(object):
    def __init__(self, product, productlayer, possiblesource_xml, scifile=None):
        self.product = product
        self.source = productlayer
        self.node = possiblesource_xml
        self.scifile = scifile

    def __str__(self):
        return etree.tostring(self.node, pretty_print=True)

    @property
    def platforms(self):
        if not hasattr(self, '_platforms'):
            if self.node.attrib['platforms'] == False:
                self._platforms = False
            else:
                self._platforms= self.node.attrib['platforms'].split(' ')
        return self._platforms

    @property
    def name(self):
        if not hasattr(self, '_name'):
            self._name = self.node.pyval
        return self._name

class Variable(object):
    def __init__(self, product, source, variable_xml, scifile=None):
        self.product = product
        self.source = source
        self.node = variable_xml
        self.scifile = scifile

    def __str__(self):
        return etree.tostring(self.node, pretty_print=True)

    @property
    def name(self):
        if not hasattr(self, '_name'):
            self._name = self.node.pyval
        return self._name

    @property
    def eq_name(self):
        if not hasattr(self, '_eq_name'):
            self._eq_name = self.node.attrib['name'] if self.node.attrib['name'] else self.name
        return self._eq_name

    @property
    def source_name(self):
        if not hasattr(self, 'source_name'):
            self._source_name = self.source.name
        return self._source_name

    @property
    def min(self):
        try:
            self._min = float(self.node.attrib['min'])
        except KeyError:
            self._min = None
        return self._min

    @property
    def max(self):
        try:
            self._max = float(self.node.attrib['max'])
        except KeyError:
            self._max = None
        return self._max

    @property
    def min_outbounds(self):
        self._min_outbounds = self.node.attrib['min_outbounds']
        return self._min_outbounds

    @property
    def max_outbounds(self):
        self._max_outbounds = self.node.attrib['max_outbounds']
        return self._max_outbounds

    @property
    def inverse(self):
        self._inverse = test_attrib_bool(self.node, 'inverse')
        return self._inverse

    @property
    def normalize(self):
        self._normalize = test_attrib_bool(self.node, 'normalize')
        return self._normalize

    @property
    def zenith_correct(self):
        self._zenith_correct = test_attrib_bool(self.node, 'zenith')
        return self._zenith_correct

    @property
    def mark_terminator(self):
        if not hasattr(self, '_mark_terminator'):
            self._mark_terminator = test_attrib_bool(self.node, 'mark_terminator')
        return self._mark_terminator

    @property
    def optional(self):
        if not hasattr(self, '_optional'):
            self._optional= test_attrib_bool(self.node, 'optional')
        return self._optional

    @property
    def units(self):
        try:
            self._units = self.node.attrib['units']
        except KeyError:
            self._units = None
        return self._units

class Dataset(object):
    def __init__(self, dataset_xml, scifile=None):
        self.node = dataset_xml
        self.scifile = scifile

    def __str__(self):
        return etree.tostring(self.node, pretty_print=True)

    @property
    def name(self):
        return self.node.pyval

class Colorbar(object):
    def __init__(self, dataset_xml=None, scifile=None):
        self.node = dataset_xml
        self.scifile = scifile

    @staticmethod
    def fromvals(cmap, ticks=None, ticklabels=None, title=None, bounds=None, norm=None):
        cbar = Colorbar()
        cbar._cmap = cmap
        cbar._ticks = ticks
        if not ticks:
            cbar._ticks = []
        cbar._ticklabels = ticklabels
        if not ticklabels:
            cbar._ticklabels = []
        cbar._title = title
        cbar._bounds = bounds
        cbar._norm = norm
        return cbar

    def __str__(self):
        return etree.tostring(self.node, pretty_print=True)

    @property
    def cmap(self):
        if not hasattr(self, '_cmap'):
            try:
                self._cmap = self.node.find('cmap').pyval
            except AttributeError:
                self._cmap = None
        return self._cmap

    @property
    def ticks(self):
        if not hasattr(self, '_ticks'):
            try:
                self._ticks = [float(num) for num in self.node.find('ticks').pyval.strip().split()]
            except AttributeError:
                #Should this be None?
                self._ticks = []
        return self._ticks

    @property
    def ticklabels(self):
        if not hasattr(self, '_ticklabels'):
            try:
                self._ticklabels = self.node.find('ticklabels').pyval.strip().split()
            except AttributeError:
                #Should this be None?
                self._ticklabels = []
        return self._ticklabels

    @property
    def title(self):
        if not hasattr(self, '_title'):
            try:
                #self._title = self.node.find('title').pyval.strip()
                self._title = self.node.find('title').pyval.strip().decode('string_escape')
            except AttributeError:
                self._title = None
        return self._title

    @property
    def bounds(self):
        if not hasattr(self, '_bounds'):
            try:
                #self._bounds = self.node.find('bounds').pyval.strip()
                self._bounds = self.node.find('bounds').pyval.strip().decode('string_escape')
            except AttributeError:
                self._bounds = None
        return self._bounds

    @property
    def norm(self):
        if not hasattr(self, '_norm'):
            try:
                #self._norm = self.node.find('norm').pyval.strip()
                self._norm = self.node.find('norm').pyval.strip().decode('string_escape')
            except AttributeError:
                self._norm = None
        return self._norm

def test_attrib_bool(node, name, yes='yes', no='no'):
    '''Tests attribute "name" from ElementTree "node" against yes and no
    keywords.  If name == yes then return true, if name == no then return
    false, otherwise raise PFAttributeError.

    Useage:
        test_attrib_bool(node, name, yes='yes', no='no')
    
    Arguments:
        node - An lxml.ElementTree object
        name - Name of an attribute to look for as a string
    Keywords:
        yes  - Value to substitute with True
        no   - Value to substitute with False
    '''

    val = node.attrib[name]
    if val.lower() == yes:
        return True
    elif val.lower() == no:
        return False
    else:
        raise PFAttributeError('Attribute %s must be either %s or %s.' % (name, yes, no))
