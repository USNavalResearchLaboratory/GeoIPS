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
import logging
import os
from datetime import datetime

# Installed Libraries
from IPython import embed as shell
# If this reader is not installed on the system, don't fail altogether, just skip this import. This reader will
# not work if the import fails, and the package will have to be installed to process data of this type.
try: import netCDF4 as ncdf
except: print 'Failed import netCDF4 in scifile/readers/amsr2_ncdf4_reader.py. If you need it, install it.'
import numpy as np

# GeoIPS Libraries
from .reader import Reader
from ..containers import _empty_varinfo
from geoips.utils.path.datafilename import DataFileName
from geoips.utils.satellite_info import SatSensorInfo

log = logging.getLogger(__name__)

# For now must include this string for automated importing of classes.
reader_class_name = 'AMSR2_NCDF4_Reader'
class AMSR2_NCDF4_Reader(Reader):

    # The dataset_info, gvar_info, and gvar_unmasked properties lays out 
    # the structure of the SciFile object.

    # dataset_info[dataset_name][geoips_varname] = orig_datafile_varname

    # These values are used to initialize the 
    #   metadata, datavars, and gvars dictionaries 
    #   before they are passed to the reader.

    # datavars, gvars, and metadata are passed by reference,
    #   so they are modified in place by the reader and do 
    #   not have to be returned from def read.

    # These dictionaries are used to populate the 
    #   SciFile object with the appropriate information
    #   and data.  The SciFile object is a common internal
    #   format that GeoIPS uses for data processing and
    #   product and image creation.

    # datavars[dsname][geoipsvarname] = channel_data_read_from_datafile
    # gvars[dsname]['Latitude'] = latvals_for_dataset_dsname
    # gvars[dsname]['Longitude'] = lonvals_for_dataset_dsname
    # metadata['top']['METADATAFIELD'] = metadata_info_pulled_from_datafile
    # in addition to metadata['top'] (which populates the metadata on the top 
    # level SciFile object, as well as propagating to the lower
    # level dataset and variable objects), metadata also 
    # contains
    #   metadata['ds'][dsname]['METADATAFIELD']
    #   metadata['datavars'][dsname][geoipsvarname]['METADATAFIELD']
    #   metadata['gvars'][dsname]['Latitude']['METADATAFIELD']
    # these are currently unused, but may be implemented as needed.
    dataset_info = { 'TIME': {'time': 'Scan_Time'},
                     'LO': {'tb6h':'Brightness_Temperature_6_GHzH',
                            'tb6v':'Brightness_Temperature_6_GHzV',
                            'tb7h':'Brightness_Temperature_7_GHzH',
                            'tb7v':'Brightness_Temperature_7_GHzV',
                            'tb10h':'Brightness_Temperature_10_GHzH',
                            'tb10v':'Brightness_Temperature_10_GHzV',
                            'tb18h':'Brightness_Temperature_18_GHzH',
                            'tb18v':'Brightness_Temperature_18_GHzV',
                            'tb23h':'Brightness_Temperature_23_GHzH',
                            'tb23v':'Brightness_Temperature_23_GHzV',
                            'tb36h':'Brightness_Temperature_36_GHzH',
                            'tb36v':'Brightness_Temperature_36_GHzV',},
                     'HIA': { 'tb89hA': 'Brightness_Temperature_89_GHz_AH',
                              'tb89vA': 'Brightness_Temperature_89_GHz_AV',},
                     'HIB':{ 'tb89hB': 'Brightness_Temperature_89_GHz_BH',
                             'tb89vB': 'Brightness_Temperature_89_GHz_BV',},
                   }
    # Currently, internally to SciFile:
    #   Lat/Lons MUST be named specifically Latitude and Longitude. 
    #   Solar Zenith Angle MUST be named SunZenith
    gvar_info = { 'LO': {
                         'Latitude': 'Latitude_for_Low_Resolution',
                         'Longitude': 'Longitude_for_Low_Resolution',
                        },
                  'HIA': { 
                         'Latitude': 'Latitude_for_High_Resolution',
                         'Longitude': 'Longitude_for_High_Resolution',
                        },
                  'HIB': {
                         'Latitude': 'Latitude_for_89B',
                         'Longitude': 'Longitude_for_89B',
                        },
    # The following geolocation_variables are highly masked, 
    # and SciFile currently combines the mask from ALL variables that 
    # go into a dataset (this results in having 0% coverage if these
    # variables go in the LO dataset with Latitude and Longitude, since there
    # are effectively no valid lat/lons on the dataset once we apply these masks).  
    # Until this is fixed, either don't include 
    # fully masked variables if you don't need them, or list 
    # them in a separate dataset.
    # If highly masked variables NEED to be in the same dataset as 
    # the lat/lon (ie, if it is actually a variable you need to plot..),
    # then talk to Mindy.  There is a workaround available.
    # Just be aware that this can be an issue, if your data all appears to
    # disappear inexplicably.
                  'LO_UNMASKED': {
                         'GeoAziAngle': 'Earth_Azimuth_Angle',
                         'GeoIncAngle': 'Earth_Incidence_Angle',
                         'Sun_Azimuth_Angle': 'Sun_Azimuth_Angle',
                         'SunElevAngle': 'Sun_Elevation',
                         'SunGlintFlag': 'Sun_Glint_Flag',
                        # DO NOT INCLUDE (could create a new dataset for this shape if you really wanted to)
                        # 'LOFlaglo':'Land_Ocean_Flag_6_to_36' wrong shape: (2, 3961, 486) instead of (3961,486)
                        # 'PixQuallo':'Pixel_Data_Quality_6_to_36' wrong shape: (dimensions coorsepond to high-resolution)
                        },
                  'HIA_UNMASKED': {
                          'Pixel_Data_Quality_89':'Pixel_Data_Quality_89',
                          # DO NOT INCLUDE (could create a new dataset for this shape if you really wanted to)
                          #'LOFlaghi':'Land_Ocean_Flag_89' is the wrong shape - shape (2, 3840, 486) LOFlaghi
                          #                                                     shape (3840, 486) Latitude
                        },
                }
                        

    # Note ALL variable/source/platform names must match between 
    #    scifile/readers/MYREADER.py
    #    productfiles/<SOURCE_NAME>/<PRODUCT_NAME>.xml
    #    sectorfiles/static/MYAREA.xml
    #    utils/satellite_info.py

    # SOME OF THESE MAY NOT APPLY FOR ancillary data (ie, elevation files, etc).  But in any case, any time you use a variable, 
    # you must use the same name to reference it as you set in the reader's dataset_info property.

    # Example: <VARIABLE_NAME>=tb89ha, <SOURCE_NAME>=amsr2, <PLATFORM_NAME>=gcom-w1 and <PRODUCT_NAME>=89H names must match between:
    # scifile/readers/amsr2_ncdf4_reader.py:
    #       class AMSR2_NCDF4_Reader(Reader):
    #           dataset_info = { 'HIA' : { '<VARIABLE_NAME>':'Brightness_Temperature_89_GHz_AH' } }
    #       def read:
    #           metadata['top']['platform_name'] = df.platform_name.lower() # MUST MATCH <PLATFORM_NAME>
    #           metadata['top']['source_name'] = df.instrument_name.lower() # MUST MATCH <SOURCE_NAME>
 
    # productfiles/amsr2/89H.xml (DOES NOT APPLY FOR ANCILLARY DATA):
    # <product method='basic' name='{PRODUCT_NAME}' testonly='yes'>
    #    <basic_args>
    #        <source name='{SOURCE_NAME}'>
    #            <var>{VARIABLE_NAME}</var>

    # sectorfiles/static/Areas.xml (DOES NOT APPLY FOR ANCILLARY DATA):
    #    <source name="{SOURCE_NAME}">
    #      <product name="{PRODUCT_NAME}"/>

    # utils/satellite_info.py
    #    SensorInfo_classes = {
    #       '<SOURCE_NAME>: AMSR2SensorInfo,

    #    SatInfo_classes = {
    #       '<PLATFORM_NAME>: GCOMSatInfo,

    @staticmethod
    def format_test(fname):
        # This reader only handles individual files, not multiple files or directories.
        # Change def read and def format_test if you want to handle directories directly.
        if os.path.isdir(fname):
            return False

        # Check that this file is ncdf4 first
        from ..file_format_tests import ncdf4_format_test
        if not ncdf4_format_test(fname):
            return False

        df = ncdf.Dataset(str(fname), 'r')

        # Uncomment this shell statement for development purposes.
        #print 'Entering shell statement in format_test for development purposes'
        #shell()

        # When it drops to shell, poke around in the resulting "df" object 
        # until you find something UNIQUE to the current data type.  
        # We just need this "format_test" method within the reader to return 
        # True when this netcdf is UNIQUELY an amsr2 netcdf file, 
        # and False if it is a netcdf for a different sensor.

        # Some IPython data file interrogation tips (PLEASE NOTE ALL OF 
        # these tips WILL NOT work with all data types! Different data files
        # have different attributes/properties on the resulting python objects):
        #   df.<TAB> 
        #       shows a list of properties and methods you have available on 
        #       the df object
        #   df.attributes().keys() 
        #       shows what dictionary elements are available in df.attributes()
        #   attrs = df.attributes() 
        #   attrs['KeyVal']
        #       Access the element named 'KeyVal' in the dictionary attrs
        #   attrs.<TAB>
        #       <TAB> does not work after a function or dictionary element, 
        #       so you have to create a new variable, then use <TAB> on the 
        #       new variable to access it's list of properties and methods
        # df.project now 'NPP Data Exploitation: NOAA GCOM-W1 AMSR2', not just NOAA GCOM-W1 AMSR2
        if hasattr(df,'project') and 'NOAA GCOM-W1 AMSR2' in df.project:
            return True
        return False


    # Note you may not need to use sector_definition and/or chans, 
    # but it is there if you need it (could be used to only read 
    # in a subset of the data. In general to start, you may just 
    # want to read everything in and ignore sector_definition and/or chans)

    # datavars, gvars, and metadata contain all of the data being read. 
    #   They are passed by reference,so they are modified in place by the 
    #   reader and do not have to be returned from def read. 
    # Note if SciFile.import_data() was called on a directory, the reader 
    #   is called individually on each file, and the data dictionaries 
    #   will contain all of the data from all files (it will append data
    #   with each successive call). So just populate the datavars/gvars/metadata
    #   on each file appropriately, and SciFile should automatically create
    #   the object with all of the data.
    def read(self,fname,datavars,gvars,metadata,chans=None,sector_definition=None):

        # Use the appropriate python based reader for opening the current data 
        # type. This package must be installed on the system, and imported above
        # in the "Installed Libraries" import section.
        df = ncdf.Dataset(str(fname), 'r')

        # Uncomment this shell statement in order to interrogate the data file 
        # and determine what attributes and fields need to be read from the 
        # data file.
        #print 'Entering IPython shell in '+self.name+' for development purposes'
        #shell()

        # Grab necessary metadata that will populate the _finfo, 
        # _dsinfo, and _varinfo properties on the SciFile object.
        # The available fields for varinfo can be found in 
        # scifile/containers.py at the beginning of the file.
        # Additional options available with the metadata dictionary
        # can be found in the comments with the dataset_info property above.
        metadata['top']['start_datetime'] = datetime.strptime(df.time_coverage_start.split('.')[0],'%Y-%m-%dT%H:%M:%S')
        # Note an apparent bug in productfilename uses end_datetime as filename. 
        # For now just leave out end_datetime (it automatically gets set to start_datetime
        # in scifile if undefined)
        # Ooops, this might have messed up pass predictor
        metadata['top']['end_datetime'] = datetime.strptime(df.time_coverage_end.split('.')[0],'%Y-%m-%dT%H:%M:%S')
        metadata['top']['dataprovider'] = 'unknown'
        # DOC/NOAA/NESDIS/OSPO > Office of Satellite and Product Operations,     NESDIS, NOAA, U.S. Department of
        # Commerce
        if 'DOC/NOAA/NESDIS/OSPO' in df.institution:
            metadata['top']['dataprovider'] = 'noaa-nesdis-ospo'
        elif 'NOAA' in df.institution and 'NESDIS' in df.institution:
            metadata['top']['dataprovider'] = 'noaanesdis'
        elif 'NOAA' in df.institution:
            metadata['top']['dataprovider'] = 'noaa'
        metadata['top']['filename_datetime'] = metadata['top']['start_datetime']

        # Tells driver to NOT try to sector this data.
        metadata['top']['NON_SECTORABLE'] = True

        # platform_name and source_name MUST match values found 
        # in SensorInfo_classes and SatInfo_classes in utils/satellite_info.py. 
        # Those are the keys used throughout GeoIPS for determining what data 
        # type we are working with. If opening the SatSensorInfo object fails,
        # raise an Error and stop operation.
        
        # source_name = 'amsr2'
        # platform_name = 'gcom-w1'
        metadata['top']['platform_name'] = df.platform_name.lower()
        metadata['top']['source_name'] = df.instrument_name.lower()
        si = SatSensorInfo(metadata['top']['platform_name'],metadata['top']['source_name'])
        if not si:
            raise SciFileError('Unrecognized platform and source name combination: '+metadata['top']['platform_name']+' '+metadata['top']['source_name'])

        # Use filename field for filename_datetime if it is available.
        # Else, just use the start_datetime we found from the data
        # above. Note we ALWAYS want to have a default if DataFileName
        # is not defined.  We do not want to rely on having our specific 
        # internal filename format in order to process, but if we have 
        # additional information available from the data filename, we
        # can use it.
        dfn = DataFileName(os.path.basename(fname)) 
        if dfn:
            sdfn = dfn.create_standard()
            metadata['top']['filename_datetime'] = sdfn.datetime


        # chans == [] specifies we don't want to read ANY data, just metadata.
        # chans == None specifies that we are not specifying a channel list, 
        #               and thus want ALL channels.
        if chans == []:
            # If NO CHANNELS were specifically requested, just return at this 
            # point with the metadata fields populated. A dummy SciFile dataset 
            # will be created with only metadata. This is for checking what 
            # platform/source combination we are using, etc.
            return 


        # Set up the dictionaries of variables that will go in each dataset.
        #       datavars: actual channel data
        #       gvars:    geolocation variable data 
        #                 specifically named:
        #                 Latitude (REQUIRED), 
        #                 Longitude (REQUIRED), and 
        #                 SunZenith (optional, required for day/night 
        #                 discrimination) 

        # Each data variable array and geolocation variable array of a 
        #   specific dataset_name MUST be the same shape

        # datavars[dataset_name][geoips_varname] = geoips_varname_channel_data
        # gvars[dataset_name]['Latitude'] = dataset_name_lat_numpy_array
        # gvars[dataset_name]['Longitude'] = dataset_name_lon_numpy_array
        # *OPTIONAL* gvars[dataset_name]['SunZenith'] = dataset_name_sunzenith_numpy_array
        
        # geoips_varname_channel_data.shape == dataset_name_lat_numpy_array.shape 
        #   == dataset_name_lon_array.shape == dataset_name_sunzenith_numpy_array.shape

        # Only datavars and gvars with the same shape can go in the same dataset.

        # See additional datavars and gvars dictionary structure information
        #       found in the comments above, with the dataset_info property of this reader.


        # Loop through each dataset name found in the dataset_info property above.
        for dsname in self.dataset_info.keys():
            # Loop through the variables found in the current dataset
            # The dataset_info dictionary maps the geoips varname to the
            # varname found in the original datafile
            for geoipsvarname,ncvarname in self.dataset_info[dsname].items():
                # If we requested specific channels, and the current channel
                # is not in the list, skip this variable.
                if chans and geoipsvarname not in chans:
                    continue
                # Read the current channel data into the datavars dictionary
                log.info('    Reading '+dsname+' channel "'+ncvarname+'" from file into SciFile channel: "'+geoipsvarname+'"...')
                # Read ncvarname from the original datafile into datavars[dsname][geoipsvarname]
                datavars[dsname][geoipsvarname] = np.ma.masked_equal(df.variables[ncvarname][...],df.variables[ncvarname]._FillValue)

        # Loop through each dataset name found in the gvar_info property above.
        for dsname in self.gvar_info.keys():
            # Loop through the variables found in the current dataset
            # The gvar_info dictionary maps the geoips varname to the
            # varname found in the original datafile
            for geoipsvarname,ncvarname in self.gvar_info[dsname].items():
                # Read the current channel data into the datavars dictionary
                log.info('    Reading '+dsname+' channel "'+ncvarname+'" from file into SciFile channel: "'+geoipsvarname+'"...')
                # Read ncvarname from the original datafile into datavars[dsname][geoipsvarname]
                gvars[dsname][geoipsvarname] = np.ma.masked_equal(df.variables[ncvarname][...],df.variables[ncvarname]._FillValue)


        # datavars, gvars, and metadata are passed by reference, so we do not have to return anything.
