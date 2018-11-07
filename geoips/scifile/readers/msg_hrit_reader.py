# 20170330 MLS Try to only decompress what we need (VERY filename dependent), 
#               make scifile and hrit channel names match (more filename dependence),
#               don't try to decompress/open file for import_metadata (more filename dependence for time).
#               satpy requires time to open file, and requires standard (decompressed) filenames, 
#               so built in filename dependence by using satpy

# Python Standard Libraries
import logging
import os
from datetime import datetime
from glob import glob
from subprocess import call

# Installed Libraries
from IPython import embed as shell
try: from satpy.scene import Scene
except: print 'Failed import satpy.scene in scifile/readers/msg_hrit_reader.py. If you need it, install it.'

## If this reader is not installed on the system, don't fail altogether, just skip this import. This reader will
## not work if the import fails, and the package will have to be installed to process data of this type.
#from mpop.satellites import GeostationaryFactory
#from mpop.projector import get_area_def
#from mpop.utils import debug_on
#debug_on()
import datetime
#from mipp.xrit.sat import load

import numpy as np

# GeoIPS Libraries
from .reader import Reader
from ..containers import _empty_varinfo
from geoips.utils.path.datafilename import DataFileName
from geoips.utils.satellite_info import SatSensorInfo
from geoips.utils.plugin_paths import paths as gpaths

log = logging.getLogger(__name__)

# For now must include this string for automated importing of classes.
reader_class_name = 'MSG_XRIT_Reader'
class MSG_XRIT_Reader(Reader):

    dataset_info = { 
                          'LO': {'VIS006':'VIS006',
                                 'VIS008':'VIS008',
                                 'IR_016':'IR_016',
                                 'IR_039':'IR_039',
                                 'IR_087':'IR_087',
                                 'IR_097':'IR_097',
                                 'IR_108':'IR_108',
                                 'IR_120':'IR_120',
                                 'IR_134':'IR_134',
                                 'WV_062':'WV_062',
                                 'WV_073':'WV_073',},
                          'HI': { 'HRV': 'HRV',},
                        }

    # Decompress the Meteosat-8 files from

    @staticmethod
    def decompress_msg(fname,outdir,chans):
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        cwd = os.getcwd()
        os.chdir(outdir)
        log.info('Decompressing to '+outdir)
        for filename in glob(os.path.join(fname, '*')):
            needchan = False
            #if os.path.isfile(filename) and filename.split('-')[-1] == '__' and 'PRO' not in filename and 'EPI' not in filename:
            #    log.info('Original file already decompressed: '+filename)
            # If files are already decompressed, xRITDecompress just copies them to output location.
            # This will force users to have xRITDecompress installed to use this reader at all.
            if os.path.isfile(filename):
                if chans:
                    for chan in chans:
                        if chan in filename:
                            needchan = True
                if chans == None or 'PRO' in filename or 'EPI' in filename or needchan:
                    # Changes from -C_ to -__ for decompressed version. PRO and EPI still -__
                    outfile = os.path.join(outdir,os.path.basename(filename[0:-2]+'__'))

                    # If the outfile doesn't already exists, XRIT_DECOMPRESS_PATH is set, 
                    # and XRIT_DECOMPRESS_PATH actually points to a file, then 
                    if not os.path.isfile(outfile) \
                      and os.getenv('XRIT_DECOMPRESS_PATH') \
                      and os.path.isfile(os.getenv('XRIT_DECOMPRESS_PATH')):
                        call([os.getenv('XRIT_DECOMPRESS_PATH'),filename]) 

                    # If the outfile already exists, skip
                    elif os.path.isfile(outfile):
                        log.info('Already decompressed '+os.path.basename(outfile))

                    # If XRIT_DECOMPRESS_PATH is not set, fail.
                    elif not os.getenv('XRIT_DECOMPRESS_PATH'):
                        log.error('Must install xRITDecompress software and set XRIT_DECOMPRESS_PATH to the full path to the software.')  
                        log.error('    See http://www.eumetsat.int/website/home/Data/DataDelivery/SupportSoftwareandTools/index.html')
                        log.error('    for Public Wavelet Transform Decompression Library Software - requires license.')

                    # If XRIT_DECOMPRESS_PATH is set, but the file doesn't exist, error.
                    elif os.getenv('XRIT_DECOMPRESS_PATH') and not os.path.isfile(os.getenv('XRIT_DECOMPRESS_PATH')):
                        log.error('xRITDecompress software not found at XRIT_DECOMPRESS_PATH location: '+os.getenv('XRIT_DECOMPRESS_PATH'))
                        log.error('    See http://www.eumetsat.int/website/home/Data/DataDelivery/SupportSoftwareandTools/index.html')
                        log.error('    for Public Wavelet Transform Decompression Library Software - requires license -')
                        log.error('    and set XRIT_DECOMPRESS_PATH environment variable to the install location.')

                    else:
                        log.info('Skipping file, not sure why...')

        os.chdir(cwd)

    @staticmethod
    def format_test(fname):
        #
        #  /satdata/realtime/seviri/meteoIO/meteosat8_nesdisstar-hrit/20170215/000000
        #
        if not os.path.isdir(fname):
            return False
        singlefname = glob(os.path.join(fname, '*'))[0]
        if singlefname.split('-')[-1] != '__' and singlefname.split('-')[-1] != 'C_' and os.path.splitext(singlefname)[-1] != '.hrit' :
            return False

        return True


    def read(self,fname,datavars,gvars,metadata,chans=None,sector_definition=None):

        # Use filename field for filename_datetime if it is available.
        dfn = DataFileName(os.path.basename(glob(os.path.join(fname, '*'))[0]))
        if dfn:
            sdfn = dfn.create_standard()
            metadata['top']['filename_datetime'] = sdfn.datetime

        metadata['top']['start_datetime'] = sdfn.datetime
        metadata['top']['end_datetime'] = sdfn.datetime
        metadata['top']['dataprovider'] = 'nesdisstar'
        metadata['top']['platform_name'] = sdfn.satname
        metadata['top']['source_name'] = 'seviri'
        # MUST be set on readers that sector at read time.
        # Affects how reading/processing is done in driver.py
        metadata['top']['sector_definition'] = sector_definition
        metadata['top']['SECTOR_ON_READ'] = True

        si = SatSensorInfo(metadata['top']['platform_name'],metadata['top']['source_name'])
        if not si:
            raise SciFileError('Unrecognized platform and source name combination: '+metadata['top']['platform_name']+' '+metadata['top']['source_name'])

        # chans == [] specifies we don't want to read ANY data, just metadata.
        # chans == None specifies that we are not specifying a channel list,
        #               and thus want ALL channels.
        if chans == []:
            # If NO CHANNELS were specifically requested, just return at this
            # point with the metadata fields populated. A dummy SciFile dataset
            # will be created with only metadata. This is for checking what
            # platform/source combination we are using, etc.
            return

        outdir = os.path.join(gpaths['LOCALSCRATCH'],os.path.dirname(sdfn.name))
        self.decompress_msg(fname,outdir,chans)
        try:
            global_data = Scene(platform_name="Meteosat-8", sensor="seviri",reader="hrit_msg",
                    start_time = sdfn.datetime, base_dir=outdir)
        except TypeError:
            global_data = Scene(filenames=glob(os.path.join(outdir,'*')),reader="hrit_msg",
                filter_parameters = { 'start_time': sdfn.datetime } )
        metadata['top']['start_datetime'] = global_data.start_time
        metadata['top']['end_datetime'] = global_data.end_time


        # Loop through each dataset name found in the dataset_info property above.
        for dsname in self.dataset_info.keys():
            # Loop through the variables found in the current dataset
            # The dataset_info dictionary maps the geoips varname to the
            # varname found in the original datafile
            for geoipsvarname,spvarname in self.dataset_info[dsname].items():
                # If we requested specific channels, and the current channel
                # is not in the list, skip this variable.
                if chans and geoipsvarname not in chans:
                    continue
                # Read the current channel data into the datavars dictionary
                log.info('    Initializing '+dsname+' channel "'+spvarname+'" from file into SciFile channel: "'+geoipsvarname+'"...')
                global_data.load([spvarname])
                # Read spvarname from the original datafile into datavars[dsname][geoipsvarname]
        ad = sector_definition.area_definition
        log.info('    Sectoring data to '+ad.name+' ...')
        sectored_data = global_data.resample(ad)
        for spvarname in sectored_data.datasets.keys():
            for dsname in self.dataset_info.keys():
                for geoipsvarname in self.dataset_info[dsname].keys():
                    if self.dataset_info[dsname][geoipsvarname] == spvarname.name:
                        if 'Longitude' not in gvars[dsname].keys():
                            log.info('    Saving Longitude to gvars')
                            gvars[dsname]['Longitude'] = np.ma.array(ad.get_lonlats()[0])
                        if 'Latitude' not in gvars[dsname].keys():
                            log.info('    Saving Latitude to gvars')
                            gvars[dsname]['Latitude'] = np.ma.array(ad.get_lonlats()[1])
                        if 'SunZenith' not in gvars[dsname].keys():
                            from geoips.scifile.solar_angle_calc import satnav
                            log.info('        Using satnav, can only calculate Sun Zenith angles')
                            gvars[dsname]['SunZenith'] = satnav('SunZenith',metadata['top']['start_datetime'],gvars[dsname]['Longitude'],gvars[dsname]['Latitude'])
                        self.set_variable_metadata(metadata, dsname, geoipsvarname)
                        try:
                            datavars[dsname][geoipsvarname] =\
                             np.ma.array(sectored_data.datasets[spvarname.name].data,
                             mask=sectored_data.datasets[spvarname.name].mask)
                            log.warning('Sectored variable %s '%(spvarname.name))
                        except AttributeError:
                            log.warning('Variable %s does not contain a mask, masking invalid values! Might take longer'%(spvarname.name))
                            datavars[dsname][geoipsvarname] =\
                                np.ma.masked_invalid(sectored_data.datasets[spvarname.name].data)

        # datavars, gvars, and metadata are passed by reference, so we do not have to return anything.

    @staticmethod
    def set_variable_metadata(scifile_metadata, dsname, varname):
        if dsname not in scifile_metadata['datavars'].keys():
            scifile_metadata['datavars'][dsname] = {}
        if varname not in scifile_metadata['datavars'][dsname].keys():
            scifile_metadata['datavars'][dsname][varname] = {}
        wavelength = varname.replace('VIS','').replace('IR_','').replace('WV_','')
        wavelength = float(wavelength[0:2]+'.'+wavelength[2])
        scifile_metadata['datavars'][dsname][varname]['wavelength'] = wavelength
