#!/bin/env

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

# 20160418  MLS added create_multisource_product method to do overlays.  Added flag for
#                   other_on_top for merge so we can make sure the layers merge in the right order
#                   (default to false so normal ones still work)

# Standard Python Libraries
import pdb
import os
import logging


# Installed Libraries
try:
    from IPython import embed as shell
except:
    print 'Failed import IPython in geoimg/geoimg.py. If you need it, install it.'
try: 
    from memory_profiler import profile
except: 
    print 'Failed import memory_profiler in geoimg/geoimg.py'


# GeoIPS Libraries
from . import plot
from .geoimgexceptions import NoMatchingClassError
from geoips.utils.log_setup import interactive_log_setup
from geoips.utils.plugin_paths import paths as gpaths



log = interactive_log_setup(logging.getLogger(__name__))
products_db = gpaths['SATOPS']+'/longterm_files/databases/products.db'



def add_to_products_db(geoimgobj):

    cc,conn = open_products_db()

    cc.execute("SELECT * FROM atcf_deck_stormfiles WHERE filename = ?", (atcf_stormfilename,))
    data = cc.fetchall()
    if data:
        log.info('Already in database ?! Skipping')
        return data
    log.info('')
    # Need to actually pull the values from geoimgobj.
    cc.execute('''insert into products_db(
                    filename,
                    ext text,
                    last_updated,
                    op_start_datetime,
                    op_end_datetime,
                    sector_name,
                    product_name,
                    resolution,
                    min_lat,
                    min_lon,
                    max_lat,
                    max_lon,
                    coverage,
                    data_provider,
                    tc_start_vmax,
                    tc_start_name,
                    tc_vmax,
                    ) values(?, ?, ?, ?,?,?,?,?,?,?,?)''', 
                    (atcf_stormfilename,
                        filename,
                        ext,
                        last_updated,
                        op_start_datetime,
                        op_end_datetime,
                        sector_name,
                        product_name,
                        resolution,
                        min_lat,
                        min_lon,
                        max_lat,
                        max_lon,
                        coverage,
                        data_provider,
                        tc_start_vmax,
                        tc_start_name,
                        tc_vmax,
                        ))
    conn.close()
    return data

def open_products_db(db=products_db):

    # Make sure the directory exists.  If the db doesn't exist,
    # the sqlite3.connect command will create it - which will
    # fail if the directory doesn't exist.
    if not os.path.exists(os.path.dirname(db)):
        os.makedirs(os.path.dirname(db))

    conn = sqlite3.connect(db)
    cc = conn.cursor()
    # Try to create the table - if it already exists, it will just fail 
    # trying to create, pass, and return the already opened db.
    try:
    	cc.execute('''CREATE TABLE GeoIPS_Products
            (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                filename text, 
                ext text,
                last_updated timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
                op_start_datetime timestamp, 
                op_end_datetime timestamp, 
                sector_name integer,
                product_name text,
                resolution real,
                min_lat real, 
                min_lon real, 
                max_lat real, 
                max_lon real, 
                coverage real,
                data_provider text,
                start_vmax real, 
                start_name real, 
                vmax real, 
                end_datetime timestamp)''')
    except sqlite3.OperationalError:
        pass
    return cc,conn






class GeoImg(object):
    #geoimg_classes = {'footprints': FootprintsImg,
    #                  'barbs': BarbsImg,
    #                  'rgb':   RGBImg,
    #                  'basic': BasicImg,
    #                  'blank': BlankImg,
    #                  'external': ExternalImg
    #                 }
    def __new__(typ, datafile, sector, intermediate_data_output=False,sectorfile=None, product=None):
        available_methods = []
        for modulename in plot.__all__:
            module = getattr(plot,modulename)
            if not hasattr(module,'plot_class_name') or not hasattr(module,'plot_method_name'):
                continue
            available_methods += [module.plot_method_name]
            if product and module.plot_method_name == product.method:
                plotter = getattr(module,module.plot_class_name)
                return plotter(datafile, sector, intermediate_data_output=intermediate_data_output,sectorfile=sectorfile, product=product)
        raise NoMatchingClassError('No matching class found for product: '+product.name+', method:'
                                   +product.method+', available methods: '+str(available_methods)+
                                   '\nNote: all GeoImg subclasses should have plot_class_name and plot_method_name defined')



