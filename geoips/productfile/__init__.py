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
import logging
import glob
from collections import OrderedDict
from datetime import datetime, timedelta

# Installed Libraries
from IPython import embed as shell


# GeoIPS Libraries
from .xml import XMLProductFile#, AllProductFiles
import geoips.utils.plugin_paths as plugins


__all__ = ['open', 'get_productfile_class', 'get_sensornames', 'get_sensor_productnames',
           'get_sensor_products', 'get_product_sensors', 'open2', 'open_product'
          ]

log = logging.getLogger(__name__)

productfile_classes = {'.xml': XMLProductFile,
                      }

pfpaths = plugins.paths['PRODUCTFILEPATHS']

def open(paths=pfpaths, suffix='xml', recursive=False, maxdepth=None, depth=0, scifile=None):
    '''Opens all product files in the given list of paths.
        INPUTS:
            paths: LIST
                paths to search (should be level ABOVE sensor directory names) 
                each element of list can either be a directory full of 
                    productfiles, or a single productfile.
                DEFAULT: PRODUCTFILEPATHS
            suffix: STRING
                allowed suffixes (currently only xml supported, should
                    add support for other productfile types at a later date)
                DEFAULT: 'xml'
            recursive: BOOLEAN
                should we recurse through each directory or not?
                DEFAULT: False
            maxdepth: INTEGER
                limits the number of layers the function will recursively
                    look through.
                DEFAULT: None (don't limit number of layers)
            depth: INTEGER
                Should increment as we recurse, but not sure that it 
                    does... Don't pass this explicitly, will be passed
                    recursively by the function itself.
                DEFAULT: 0
    '''
    log.debug('productfile.open')
    log.debug('    Productfile path: %s' % str(paths))
    productfile = None
    # Check if a single productfile was passed - if so, just open it and return.
    if len(paths) == 1 and paths[0].split('.')[-1] == suffix:
        log.debug('    Opening product file: %s' % paths[0])
        productfile = os.path.abspath(paths[0])
        pf_class = get_productfile_class(productfile)
        return pf_class(productfile, scifile=scifile)
    # If we were passed multiple files, or one or more paths, loop through,
    # recursively calling open to open each file we find.
    for path in paths:
        if not path:
            continue
        path = os.path.abspath(path)
        # If it's a directory, recursively call open on each directory
        if os.path.isdir(path):
            files = glob.glob(path+'/*')
            for pf in files:
                if os.path.isdir(pf) and (recursive is False or depth == maxdepth):
                    continue
                elif productfile is None:
                    productfile = open([pf], depth=depth, scifile=scifile)
                else:
                    curr_pf = open([pf], scifile=scifile)
                    if curr_pf is not None:
                        productfile.join(curr_pf)
            productfile.name = path
            return productfile
        # Now we recursively open each file we find in each directory.
        elif path.split('.')[-1] == suffix:
            log.debug('    Opening product file: %s' % path)
            productfile = os.path.abspath(path)
            pf_class = get_productfile_class(productfile)
            return pf_class(productfile, scifile=scifile)
        # Skip everything else.
        else:
            #Silently skip files that do not end in .xml
            pass

def get_productfile_class(productfile):
    basename, extension = os.path.splitext(productfile)
    return productfile_classes[extension]

def get_sensornames(paths=pfpaths):
    '''Pass a list of paths to search, will return all sensors''' 
    xml_files = []
    for path in paths:
        if not path:
            continue
        xml_files += glob.glob(path+'/*/*.xml')
    names = list( set([os.path.basename(os.path.dirname(f)) for f in xml_files]) )
    names.sort()
    return names

def get_sensor_productnames(sensor, paths=pfpaths):
    '''Inputs:
        sensor: string 
            sensorname
        paths: list  
            paths to search (should be level ABOVE sensor directory names) 
            default plugins PRODUCTFILEPATHS
       Returns:
        sorted list containing all productnames for given sensor''' 
    sensor_xml_files = []
    for path in paths:
        if not path:
            continue
        sensor_xml_files += glob.glob('/'.join([path, sensor, '*.xml']))
    names = list( set([os.path.basename(f).replace('.xml', '') for f in sensor_xml_files]) )
    names.sort()
    return names

def get_sensor_products(paths=pfpaths):
    '''Inputs:
        paths: list  
            paths to search (should be level ABOVE sensor directory names) 
            default plugins PRODUCTFILEPATHS
       Returns a sorted dictionary with the sensors as keys and the products as elements'''
    sensors = get_sensornames(paths)
    sensor_products = OrderedDict()

    for sensor in sensors:
        sensor_products[sensor] = get_sensor_productnames(sensor,paths)
    return sensor_products

def get_product_sensors(paths=pfpaths):
    '''Inputs:
        paths: list  
            paths to search (should be level ABOVE sensor directory names) 
            default plugins PRODUCTFILEPATHS
       Returns a sorted dictionary with the products as keys and the sensors as elements'''
    sensors = get_sensornames(paths)
    product_sensors = {}
    product_sensors_sorted = OrderedDict()

    for sensor in sensors:
        for product in get_sensor_productnames( sensor ):
            if not product_sensors.has_key(product):
                product_sensors[product] = [sensor]
            else:
                product_sensors[product].append(sensor)

    # Make a sorted verison of the dictionary
    products = product_sensors.keys()
    products.sort()
    for product in products:
        product_sensors_sorted[product] = product_sensors[product]

    return product_sensors_sorted

#NEW STUFF FOR CLEANED UP GEOIPS!!!

def open2(sensor, productlist=[], paths=pfpaths, scifile=None):
    '''
    Opens all productfiles in a given set of paths for given sensor.
    Inputs:
        sensor: string
            sensorname, must match directory within productfiles directory.
        productlist: list
            list of desired products
            default [], results in returning all products
        paths: list  
            paths to search (should be level ABOVE sensor directory names) 
            default plugins PRODUCTFILEPATHS
    '''
    #Make product names lowercase
    productlist = [prod.lower() for prod in productlist]

    # This was commented as opening ALL productfiles for ALL sensors if called
    # with no arguments, but that obviously doesn't work.  If we want to do that
    # eventually, just have to put default None for sensor, and loop through 
    # all subdirectories under pfpaths.

    #Gather dictionary of available productfiles and their product names
    products = None
    prodfiles = []
    for path in paths:
        if not path:
            continue
        globstr = os.path.join(path, sensor, '*.xml')
        for prodfile in glob.glob(globstr):
            basename = os.path.split(prodfile)[1]
            prodname = os.path.splitext(basename)[0].lower()
            #If we specified products and this product is not one of them, then continue
            if len(productlist) > 0 and prodname not in productlist:
                continue
            else:
                prodfiles += [prodfile]
                if products is None:
                    products = XMLProductFile(prodfile, scifile=scifile)
                else:
                    products.join(XMLProductFile(prodfile, scifile=scifile))
    if prodfiles:
        products.names = prodfiles
    return products

def open_product(sensor, product, paths=pfpaths, scifile=None):
    '''Opens a single product for a single sensor.
    Inputs:
        sensor: string
            sensorname, must match directory within productfiles directory.
        product: string
            desired productname 
        paths: list  
            paths to search (should be level ABOVE sensor directory names) 
            default plugins PRODUCTFILEPATHS
    Returns: XMLProductFile object
    '''
    return open2(sensor, [product],paths, scifile=scifile).open_product(product)
