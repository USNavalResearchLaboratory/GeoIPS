#!/usr/bin/env python
#
#  This is the driver routine for creation of a metoctif file for ATCF.
#  It uses the python routine tifffile.py by:
# Copyright (c) 2008-2015, Christoph Gohlke
# Copyright (c) 2008-2015, The Regents of the University of California
# Produced at the Laboratory for Fluorescence Dynamics
# All rights reserved.

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

# Standard Python Libraries
from datetime import datetime
import logging


# Installed Libraries
import numpy
try:
    #import our custom color maps
    from geoips.geoimg.output_formats.colormap import color_map_greyScale,color_map_color
except Exception as err:
    print('error importing color_map',str(err.message))
try:
    #use this package to create metoctiffs
    from skimage.external import tifffile as tf
except Exception as err:
    print('error importing tifffile',str(err.message))

try: 
    from IPython import embed as shell
except: 
    print 'Failed import IPython in geoimg/plot/metoctiff.py. If you need it, install it.'


# GeoIPS Libraries
from geoips.utils.log_setup import interactive_log_setup

#This is a display of info from the ATCF app
#*** pSatStuff->                                 ***
#***       Satellite name =                      ***
#***       nChannelNumber = 0                    ***
#***       nWidth = 1024                         ***
#***       nHeight = 1024                        ***
#***       nBitsPerPixel = 8                     ***
#***       nProjection = 4                       ***
#***       rsStandard1 = 0.000000                ***
#***       rsStandard2 = 0.000000                ***
#***       nHemisphere = 1                       ***
#***       rsBCLat = -0.898740                   ***
#***       rsBCLon = -172.800003                 ***
#***       rsUCLat = 17.498739                   ***
#***       rsUCLon = -172.800003                 ***
#***       rsULLat = 17.498739                   ***
#***       rsULLon = 177.903870                  ***
#***       rsLLLat = -0.898740                   ***
#***       rsLLLon = 177.903870                  ***
#***       rsURLat = 17.498739                   ***
#***       rsURLon = -163.503876                 ***
#***       rsLRLat = -0.898740                   ***
#***       rsLRLon = -163.503876                 ***
#***       szDescription =
#DATA_PLATFORM="himawari-8";DATA_NAME="svissr_ir1";DATA_START_TIME="Mon, 11
#Jan 2016 15:55:24 GMT";DATA_END_TIME="Mon, 11 Jan 2016 15:57:57
#GMT";DATA_UNITS="celcius";DATA_RANGE="0,249,-80,0.441767,None";

log = interactive_log_setup(logging.getLogger(__name__))

def metoctiff(self, sector, output_filename):

    log.info('Creating metoctiff image file.')

#
#  Get the image lat lon corners for the metoctiff tags
#  Added the image flip.
#

    corners = numpy.flipud(sector.area_definition.corners)

    rsULLat = int(numpy.rad2deg(corners[3].lat) * 100000)
    rsULLon = int(numpy.rad2deg(corners[3].lon) * 100000)

    rsURLat = int(numpy.rad2deg(corners[2].lat) * 100000)
    rsURLon = int(numpy.rad2deg(corners[2].lon) * 100000)

    rsLLLat = int(numpy.rad2deg(corners[0].lat) * 100000)
    rsLLLon = int(numpy.rad2deg(corners[0].lon) * 100000)

    rsLRLat = int(numpy.rad2deg(corners[1].lat) * 100000)
    rsLRLon = int(numpy.rad2deg(corners[1].lon) * 100000)

#
#  Get the center lat lon values of image for the metoctiff tags
#
    
    rsUCLat = (rsULLat + rsURLat) / 2
    rsUCLon = (rsULLon + rsURLon) / 2 

    rsBCLat = (rsLLLat + rsLRLat) /2 
    rsBCLon = (rsLLLon + rsLRLon) /2     

#
#  Info for extra tags required for metocTiff
#

    nProjection = 4 # 1 = Polar Stereographic 2 = Lambert Conformal 4 = Mercator 8 = Normal.  It's likely that mercator is analogous to 'cyl' in pyproj
    rsStandard1 = 0 #only used if lamber conformal projection is specified
    rsStandard2 = 0 #only used if lamber conformal projection is specified
    if rsBCLat >= 0:
        Hemisphere = 1 #northern
    else:
        Hemisphere = 2 #southern

#
#  The ATCF app relies heavily upon tag 270 (description) to ingest metoctiffs.  Setup the szDescription variables
#

    platform = self.title.satellite
    data_name = self.title.product
    
    if 'img' not in self.product.images.keys():
        log.info('Only single channel imagery supported at this time, skipping METOCTIFF')
        return None
    data_max = int(self.product.images['img'].max)
    data_min = int(self.product.images['img'].min)
    if self.product.images['img'].units:
        data_units = self.product.images['img'].units
    else:
        data_units = 'unknown'

#
#  The image is normalized data 0-1 and the imagey needs to be 0-255
#

    image_max = int(self.image.max() * 255)
    image_min = int(self.image.min() * 255)

#
    #  Setup the start and end time strings and convert them to metoctiff format
    #

    geoips_start_time = self.start_datetime
    data_start_time = geoips_start_time.strftime('%a, %d %b %Y %H:%M:%S GMT')
    geoips_end_time = self.end_datetime
    data_end_time = geoips_end_time.strftime('%a, %d %b %Y %H:%M:%S GMT')

#
#
#The item discription string is written to tiff tag 270 and is needed by ATCF
#

    szDescription = 'DATA_PLATFORM='+'"'+platform+'"'+';'+'DATA_NAME='+'"'+data_name+'"'+';'+'DATA_START_TIME='+'"'+data_start_time+'"'+';'+'DATA_END_TIME='+'"'+data_end_time+'"'+';'+'DATA_UNITS='+'"'+data_units+'"'+';'+'DATA_RANGE='+'"'+str(image_min)+','+str(image_max)+','+str(data_min)+','+str(data_max)+',None'+'"'+';'

#
#  Create the 8 bit image to pass to the tiff writer.
#

    data_tbs = self.image[:,:,0:3] * 255

    data_tbsint = numpy.flipud(data_tbs.astype(numpy.uint8))
    
    #TODO
    #set the color map based on the product in data_name = self.title.product
    #if data_name in ['Visible']:
        #colorMap = color_map_greyScale
    #else:
        #colorMap = color_map_color
        
    colorMap = color_map_greyScale

    # if passing in tag 320 as an extratag, TiffWriter expects a 1d array with all red values, then green values, then blue values of length 2**(data.itemsize*8)
    # if using TiffWriter.save colormap parameter, the object passed must be shape (3, 2**(data.itemsize*8)) and dtype uint16
    # not sure why reversing the color map is appropriate here, but it is
    r = colorMap[0:256]
    r.reverse()
    g = colorMap[256:512]
    g.reverse()
    b = colorMap[512:]
    b.reverse()
    #create the object to pass into the colormap parameter of TiffWriter.save
    clrmap = numpy.array([r,g,b],dtype=numpy.uint16)    
    
    # write out the file
    with tf.TiffWriter(output_filename) as mtif:
        # data shape should be image depth, height (length), width
        # after transposing just take one dimension so that a single page mtif pops out the other side
        # have only successfully loaded into ATCF mtif's with photometric (tag 262) as palette.  This setting is inferred from the data shape and the value of the colormap.
        # setting metadata=None prevents some double writing of tags that can occur during the mtif.save process that the user (me or you) may not expect to be written
        mtif.save(data_tbsint.transpose(2,0,1)[0,:,:],colormap=clrmap,description=szDescription,metadata=None,extratags=[(33000,'i',1,nProjection,True),(33001,'i',1,rsStandard1,True),(33002,'i',1,rsStandard2,True),(33003,'i',1,Hemisphere,True),(33004,'i',1,rsULLat,True),(33005,'i',1,rsULLon,True),(33006,'i',1,rsLLLat,True),(33007,'i',1,rsLLLon,True),(33008,'i',1,rsURLat,True),(33009,'i',1,rsURLon,True),(33010,'i',1,rsLRLat,True),(33011,'i',1,rsLRLon,True),(33012,'i',1,rsBCLat,True),(33013,'i',1,rsBCLon,True),(33014,'i',1,rsUCLat,True),(33015,'i',1,rsUCLon,True)])    
 
  