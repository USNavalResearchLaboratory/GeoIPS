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
from datetime import datetime
import os
import commands
import logging
import subprocess


# Installed Libraries
import numpy as np
try:
    from pyhdf.HDF import ishdf
except:
    print 'Failed import pyhdf in scifile/readers/modis_hdf4_reader.py. ' +\
            'If you need it, install it.'
try:
    from pyhdf.SD import SD, SDC
except:
    print 'Failed import pyhdf in scifile/readers/modis_hdf4_reader.py. ' +\
            'If you need it, install it.'
try:
    from pyhdf.error import HDF4Error
except:
    print 'Failed import pyhdf in scifile/readers/modis_hdf4_reader.py. ' +\
            'If you need it, install it.'
from IPython import embed as shell


# GeoIPS Libraries
from .reader import Reader
from ..containers import _empty_varinfo
from geoips.utils.path.datafilename import DataFileName

log = logging.getLogger(__name__)


# For now must include this string for automated importing of classes.
reader_class_name = 'MODIS_HDF4_Reader'


class MODIS_HDF4_Reader(Reader):

    dataset_info = {
         '1KM': ['chan20.0Rad',  # emissive 3.750 sfc/cld temp
                 'chan21.0Rad',  # emissive 3.750 sfc/cld temp
                 'chan22.0Rad',  # emissive 3.959 sfc/cld temp
                 'chan23.0Rad',  # emissive 4.050 sfc/cld temp
                 'chan24.0Rad',  # emissive 4.465 atm temperature
                 'chan25.0Rad',  # emissive 4.515 atm temperature
                 'chan27.0Rad',  # emissive 6.715 water vapor
                 'chan28.0Rad',  # emissive 7.325 water vapor
                 'chan29.0Rad',  # emissive 8.55 sfc/cld temp
                 'chan30.0Rad',  # emissive 9.73 ozone
                 'chan31.0Rad',  # emissive 11.03 sfc/cld temp
                 'chan32.0Rad',  # emissive 12.02 sfc/cld temp
                 'chan33.0Rad',  # emissive 13.335 cld top properties
                 'chan34.0Rad',  # emissive 13.635 cld top properties
                 'chan35.0Rad',  # emissive 13.935 cld top properties
                 'chan36.0Rad',  # emissive 14.235 cld top properties
                 'chan20.0BT',   # emissive 3.750 sfc/cld temp
                 'chan21.0BT',   # emissive 3.750 sfc/cld temp
                 'chan22.0BT',   # emissive 3.959 sfc/cld temp
                 'chan23.0BT',   # emissive 4.050 sfc/cld temp
                 'chan24.0BT',   # emissive 4.465 atm temperature
                 'chan25.0BT',   # emissive 4.515 atm temperature
                 'chan27.0BT',   # emissive 6.715 water vapor
                 'chan28.0BT',   # emissive 7.325 water vapor
                 'chan29.0BT',   # emissive 8.55 sfc/cld temp
                 'chan30.0BT',   # emissive 9.73 ozone
                 'chan31.0BT',   # emissive 11.03 sfc/cld temp
                 'chan32.0BT',   # emissive 12.02 sfc/cld temp
                 'chan33.0BT',   # emissive 13.335 cld top properties
                 'chan34.0BT',   # emissive 13.635 cld top properties
                 'chan35.0BT',   # emissive 13.935 cld top properties
                 'chan36.0BT',   # emissive 14.235 cld top properties
                 ],
         'Fire_Mask': ['fire_mask', ],
         'HKM': ['chan3.0Rad',   # reflective 0.470 land/cld properties
                 'chan4.0Rad',   # reflective 0.555 land/cld properties
                 'chan5.0Rad',   # reflective 1.24 land/cld properties
                 'chan6.0Rad',   # reflective 1.64 land/cld properties
                 'chan7.0Rad',   # reflective 2.13 land/cld properties
                 'chan16.0Rad',   # reflective 1.64 land/cld properties
                 'chan3.0Ref',   # reflective 0.470 land/cld properties
                 'chan4.0Ref',   # reflective 0.555 land/cld properties
                 'chan5.0Ref',   # reflective 1.24 land/cld properties
                 'chan6.0Ref',   # reflective 1.64 land/cld properties
                 'chan7.0Ref',   # reflective 2.13 land/cld properties
                 'chan16.0Ref',   # reflective 1.64 land/cld properties
                 ],
         'QKM': ['chan1.0Rad',   # reflective 0.645 land/cld boundaries
                 'chan2.0Rad',   # reflective 0.865 land/cld boundaries
                 'chan1.0Ref',   # reflective 0.645 land/cld boundaries
                 'chan2.0Ref',   # reflective 0.865 land/cld boundaries
                 ],
            }

    @staticmethod
    def format_test(fname):
        # This reader only handles individual files, not multiple files or
        # directories. Change def read and def format_test if you want to
        # handle directories directly.
        if os.path.isdir(fname):
            if 'modis_lance' in fname:
                subprocess.call(['ls', '--full-time', fname])
                log.error('Failed isdir test')
            return False

        # Check that this file is hdf4 first
        from ..file_format_tests import hdf4_format_test
        if not hdf4_format_test(fname):
            if 'modis_lance' in fname:
                subprocess.call(['ls', '--full-time', fname])
                log.error('Failed hdf4_format_test')
            return False

        if ishdf(fname):
            try:
                mf = SD(fname, SDC.READ)
            except HDF4Error:
                sdfn = DataFileName(os.path.basename(fname))
                if sdfn.sensorname == 'modis' and\
                   sdfn.dataprovider == 'modis_lance':
                    # Sometimes we download file from LANCE before it is
                    # complete on their end. Delete the bad file so we can
                    # redownload it next time
                    log.error('CORRUPT FILE incomplete download. Deleting ' +
                              'for redownload')
                    log.error(commands.getoutput('ls --full-time '+fname))
                    os.unlink(fname)
                    raise

            if 'ArchiveMetadata.0' in mf.attributes().keys() and\
               'MODIS' in mf.attributes()['ArchiveMetadata.0']:
                return True
            if 'modis_lance' in fname:
                subprocess.call(['ls', '--full-time', fname])
                log.error('Failed attribute test')
        if 'modis_lance' in fname:
            subprocess.call(['ls', '--full-time', fname])
            log.error('Failed ishdf test')
        return False

    def read(self, fname, datavars, gvars, metadata, chans=None,
             sector_definition=None):
        # Have links named starting with MOD02... for hdf2tdf conversions.
        # Unecessary, ignore.
        if os.path.islink(fname):
            log.info('        SKIPPING FILE is a link')
            return
        mf = SD(fname, SDC.READ)
        mf_metadata = parse_metadata(mf.attributes())
        # If start/end datetime happen to vary, adjust here.
        sdt = datetime.strptime(mf_metadata['RANGEBEGINNINGDATE'] +
                                mf_metadata['RANGEBEGINNINGTIME'],
                                '%Y-%m-%d%H:%M:%S')
        if not metadata['top']['start_datetime'] or\
           sdt < metadata['top']['start_datetime']:
            metadata['top']['start_datetime'] = sdt

        edt = datetime.strptime(mf_metadata['RANGEENDINGDATE'] +
                                mf_metadata['RANGEENDINGTIME'],
                                '%Y-%m-%d%H:%M:%S')
        if not metadata['top']['end_datetime'] or\
           edt > metadata['top']['end_datetime']:
            metadata['top']['end_datetime'] = edt

        # Aqua for MYD, Terra for MOD, use .lower()
        metadata['top']['platform_name'] =\
            mf_metadata['ASSOCIATEDPLATFORMSHORTNAME'].lower()
        dfn = DataFileName(os.path.basename(fname))
        # This allows you to run on arbitrarily named files and not only
        # standard filename formats
        if dfn:
            sdfn = dfn.create_standard()
            metadata['top']['filename_datetime'] = sdfn.datetime
            metadata['top']['source_name'] = sdfn.sensorname
            metadata['top']['dataprovider'] = sdfn.dataprovider
        else:
            metadata['top']['filename_datetime'] = sdt
            metadata['top']['source_name'] = 'modis'
            metadata['top']['dataprovider'] = 'unknown'
        # Use channel name from metadata so we don't have to
        # use sdfn (allows running arbitrarily named files)
        cname = mf_metadata['SHORTNAME']
        # alldata = {}
        # for ii in mf.datasets().keys():
        #     log.info('    Reading in dataset: '+ii)
        #     alldata[ii] = mf.select(ii).get()
        # for ii in mf_metadata.keys():
        #     log.info('    Reading metadata value: '+ii)

        # Create dummy dataset with metadata if we specifically requested
        # no channels
        if chans == []:
            # Will set up empty dataset in def read
            # Only need varinfo, everything else empty
            return

        datapaths = []
        datasettag = ''
        corrections = {}
        corrections_ref = {'aqua': {},
                           'terra': {}}

        if 'MOD02QKM' == cname or 'MYD02QKM' == cname:
            datapaths = ['EV_250_RefSB']
            chanlocspaths = ['Band_250M']
            datasettag = 'QKM'
            # corrections_ref[0] = scale
            # corrections_ref[1] = offset
            corrections_ref['aqua'] = {
                            'chan1.0': [0.00201941, 0],
                            'chan2.0': [0.00327573, 0],
                            }
            corrections_ref['terra'] = {
                            'chan1.0': [0.00201509, 0],
                            'chan2.0': [0.00326201, 0],
                            }
        if 'MOD02HKM' == cname or 'MYD02HKM' == cname:
            datapaths = ['EV_500_RefSB']
            chanlocspaths = ['Band_500M']
            datasettag = 'HKM'
            # corrections_ref[0] = scale
            # corrections_ref[1] = offset
            corrections_ref['aqua'] = {
                            'chan3.0': [0.00155510, 0],
                            'chan4.0': [0.00174094, 0],
                            'chan5.0': [0.00683729, 0],
                            'chan6.0': [0.0134965, 0],
                            'chan7.0': [0.0359228, -0],
                            }
            corrections_ref['terra'] = {
                            'chan3.0': [0.00155013, 0],
                            'chan4.0': [0.00173456, 0],
                            'chan5.0': [0.00682327, 0],
                            'chan6.0': [0.0134728, 0],
                            'chan7.0': [0.0358326, -0],
                            }
        if 'MOD14' == cname or 'MYD14' == cname:
            datasettag = 'Fire_Mask'
            #shell()
        if 'MOD021KM' == cname or 'MYD021KM' == cname:
            datapaths = ['EV_1KM_RefSB', 'EV_1KM_Emissive']
            datasettag = '1KM'
            chanlocspaths = ['Band_1KM_RefSB', 'Band_1KM_Emissive']
            # corrections_ref[0] = scale
            # corrections_ref[1] = offset
            corrections_ref['aqua'] = {
                            'chan8.0': [0.00185801, 0],
                            'chan9.0': [0.00170356, 0],
                            'chan10.0': [0.00164244, 0],
                            'chan11.0': [0.00172248, 0],
                            'chan12.0': [0.00171558, 0],
                            'chan13.0': [0.00209848, 0],
                            'chan13.5': [0.00209848, -0],
                            'chan14.0': [0.00215609, 0],
                            'chan14.5': [0.00215609, 0],
                            'chan15.0': [0.00250819, 0],
                            'chan16.0': [0.00333670, 0],
                            'chan17.0': [0.00347492, 0],
                            'chan18.0': [0.00372233, 0],
                            'chan19.0': [0.00371927, 0],
                            'chan26.0': [0.00889511, 0],
                            }
            corrections_ref['terra'] = {
                            'chan8.0': [0.00185398, 0],
                            'chan9.0': [0.00170009, 0],
                            'chan10.0': [0.00163386, 0],
                            'chan11.0': [0.00171776, 0],
                            'chan12.0': [0.00171045, 0],
                            'chan13.0': [0.00209057, 0],
                            'chan13.5': [0.00209057, -0],
                            'chan14.0': [0.00214607, 0],
                            'chan14.5': [0.00214607, 0],
                            'chan15.0': [0.00249967, 0],
                            'chan16.0': [0.00332639, 0],
                            'chan17.0': [0.00346232, 0],
                            'chan18.0': [0.00370446, 0],
                            'chan19.0': [0.00370657, -0],
                            'chan26.0': [0.00886857, 0],
                            }
# corrections[chan][0] = (ems1km_um) effective central wavelength in microns
# corrections[chan][1] = (tcs1km) temperature correction slope
# corrections[chan][2] = (tci1km) temperature correction intercept
            corrections = {'chan20.0': [3.7853, 9.993411E-01, 4.770532E-01],
                           'chan21.0': [3.9916, 9.998646E-01, 9.262664E-02],
                           'chan22.0': [3.9714, 9.998584E-01, 9.757996E-02],
                           'chan23.0': [4.0561, 9.998682E-01, 8.929242E-02],
                           'chan24.0': [4.4726, 9.998819E-01, 7.310901E-02],
                           'chan25.0': [4.5447, 9.998845E-01, 7.060415E-02],
                           'chan27.0': [6.7661, 9.994877E-01, 2.204921E-01],
                           'chan28.0': [7.3382, 9.994918E-01, 2.046087E-01],
                           'chan29.0': [8.5238, 9.995495E-01, 1.599191E-01],
                           'chan30.0': [9.7303, 9.997398E-01, 8.253401E-02],
                           'chan31.0': [11.0121, 9.995608E-01, 1.302699E-01],
                           'chan32.0': [12.0259, 9.997256E-01, 7.181833E-02],
                           'chan33.0': [13.3629, 9.999160E-01, 1.972608E-02],
                           'chan34.0': [13.6818, 9.999167E-01, 1.913568E-02],
                           'chan35.0': [13.9108, 9.999191E-01, 1.817817E-02],
                           'chan36.0': [14.1937, 9.999281E-01, 1.583042E-02],
                           }

        # Lat/Lons found in 1km data file appears to be downsampled to 406x271,
        # the lat/lons in MOD03 file are full 1km resolution. hkm and 1km data
        # files appear to have full 1km resolution also (2030x1354)
        # Also, the python resize function appears to just replicate the data,
        # and not interpolate. Which is not what we want.
        # print 'channel: '+sdfn.channel
        if cname == 'MOD03' or cname == 'MYD03':
            scifile_names = {'Latitude': 'Latitude',
                             'Longitude': 'Longitude',
                             'SolarZenith': 'SunZenith',
                             'SensorZenith': 'SatZenith',
                             'SolarAzimuth': 'SunAzimuth',
                             'SensorAzimuth': 'SatAzimuth'}

            for currvar in scifile_names.keys():
                sfgvar = scifile_names[currvar]
                select_data = mf.select(currvar)
                attrs = select_data.attributes()
                data = select_data.get()
                for datasettag in self.dataset_info.keys():
                    # Checking if we need this resolution based on requested
                    # channels
                    if not chans or\
                       (set(chans) & set(self.dataset_info[datasettag])):
                        log.info('    adding '+datasettag+' '+currvar)
                        pass
                    else:
                        continue

                    outdata = data
                    if datasettag == 'QKM' or datasettag == 'HKM':
                        factor = 2
                        if datasettag == 'QKM':
                            factor = 4
                        outdata = np.zeros((len(data)*factor,
                                            data.shape[1]*factor), data.dtype)
                        x = np.arange(data.shape[0])
                        y = np.arange(data.shape[1])
                        xx = np.linspace(x.min(), x.max(), outdata.shape[0])
                        yy = np.linspace(y.min(), y.max(), outdata.shape[1])
                        # kx / ky tuning factors for the interpolation ??
                        # kx/k2 must be <= 5
                        # How did this break!? Used to be
                        # scipy.interpolate.RectBivariateSpline, with import
                        # scipy above.
                        from scipy.interpolate import RectBivariateSpline
                        newKernel = RectBivariateSpline(x, y, data, kx=2, ky=2)
                        outdata = newKernel(xx, yy)
                    # Appears lat/lon does not need to be *.01, and
                    # Zenith/Azimuth do. These scale_factors are hard coded
                    # because I can't seem to easily pull them out of the big
                    # text metadata string.
                    factor = 1
                    if 'scale_factor' in attrs.keys():
                        factor = attrs['scale_factor']
                    masked_data = np.ma.masked_equal(
                        np.ma.array(outdata*factor), attrs['_FillValue'])
                    print masked_data.shape
                    # variables get propagated to top level in scifile object.
                    # geolocation_variables do not since azimuth/zenith need
                    # to be calculated for each resolution, need to be in
                    # geolocation_variables
                    #if datasettag == 'Fire_Mask':
                    #    # Duplicating 1KM lat/lons here.  Don't mask lat lons
                    #    # at all - cumulative mask results in all lat/lons
                    #    # being masked, can't register.  Need to fix
                    #    # cumulative mask issue.
                    #    gvars[datasettag][sfgvar] = masked_data
                    #    metadata['gvars'][datasettag][sfgvar] =\
                    #        _empty_varinfo.copy()
                    #    metadata['gvars'][datasettag][sfgvar]['nomask'] =\
                    #        True
                    #else:
                    #    gvars[datasettag][sfgvar] = masked_data
                    #    metadata['gvars'][datasettag][sfgvar] =\
                    #        _empty_varinfo.copy()
                    #    metadata['gvars'][datasettag][sfgvar]['nomask'] =\
                    #        False
                    # Read lat/lons directly from MOD14.
                    gvars[datasettag][sfgvar] = masked_data
                    metadata['gvars'][datasettag][sfgvar] =\
                        _empty_varinfo.copy()
                    metadata['gvars'][datasettag][sfgvar]['nomask'] =\
                        False
        elif ('MOD14' == cname or 'MYD14' == cname) and 'fire_mask' in chans:
            # Put shell statement here to figure out how to correct fire_mask
            #shell()
            fire_mask = mf.select('fire mask').get()
            masked_data = np.ma.masked_less(np.ma.array(fire_mask), 7)
            datavars[datasettag]['fire_mask'] = masked_data
            scifile_names = {'latitude': 'Latitude',
                             'longitude': 'Longitude', }
            # Read lat/lons directly out of MOD14 file, don't need satzenith,
            # etc

            for currvar in scifile_names.keys():
                sfgvar = scifile_names[currvar]
                data = mf.select(currvar).get()
                gvars[datasettag][sfgvar] = np.ma.array(data)
                metadata['gvars'][datasettag][sfgvar] =\
                    _empty_varinfo.copy()
                metadata['gvars'][datasettag][sfgvar]['nomask'] =\
                    True
        else:
            for ii in range(len(datapaths)):
                # print 'adding datapath: '+str(ii)
                datapath = datapaths[ii]
                chanlocspath = chanlocspaths[ii]
                select_alldata = mf.select(datapath)
                chanlocs = mf.select(chanlocspath).get()

                alldata = select_alldata.get()
                attrs = select_alldata.attributes()
                for jj in range(len(chanlocs)):
                    channame = 'chan'+str(chanlocs[jj])
                    if not chans or channame+'Rad' in chans or\
                       channame+'Ref' in chans or channame+'BT' in chans:
                        pass
                    else:
                        continue
                    # print 'adding channame: '+str(channame)
                    # Note the order of scale and offset. Apparently
                    # viirs / terascan do it
                    # data*scale + offset.
                    # MODIS is (data - offset)*scale
                    # STORE AS chan31Rad (ALL CHANNELS STORE DATA AS
                    # RADIANCES!!!!!!!)
                    ind = jj 
                    if len(attrs['radiance_offsets']) == 1:
                        ind = 0
                    data = (alldata[jj]-attrs['radiance_offsets'][ind]) *\
                        attrs['radiance_scales'][ind]
                    masked_data = np.ma.masked_equal(np.ma.array(data),
                                                     attrs['_FillValue'])
                    masked_data = np.ma.masked_greater(masked_data,
                                                       attrs['valid_range'][1])
                    masked_data = np.ma.masked_less(masked_data,
                                                    attrs['valid_range'][0])
                    log.info('    Adding channame: '+str(channame+'Rad') +
                             ' offset: '+str(attrs['radiance_offsets'][ind]) +
                             ' scale: '+str(attrs['radiance_scales'][ind]))
                    datavars[datasettag][channame+'Rad'] = masked_data
                    if channame in corrections.keys():
                        # cor[0] = ems1kmum, cor[1] = tcs1km, cor[2] = tci1km
                        cor = corrections[channame]
                        h = 6.626176E-34
                        c = 2.99792458E+8
                        bc = 1.380658E-23
                        # if channame == 'chan31.0':
                        #    shell()

                        data1 = np.log(1+2*h*c*c/(cor[0]*cor[0]*cor[0]
                                                  * cor[0]*cor[0]*1.0e-30
                                                  * masked_data*1.0e6))
                        data2 = (h*c/(bc*cor[0]*1.0e-6)/data1)
                        masked_data = ((data2-cor[2])/cor[1]) - 273.15

                        # Terascan conversion
                        # lam = cor[0]*1.0e-6
                        # rad_pl = masked_data*1.0e6
                        # t1 = h*c/(bc*lam)
                        # t2 = np.log(1.0+2.0*h*c*c/(lam*lam*lam*lam*lam*rad_pl))
                        # masked_data = (t1/t2) 
                        # masked_data = (masked_data - cor[2])/cor[1] - 273.15

                        log.info('    Adding channame: '+str(channame+'BT') +
                                 ' offset: ' +
                                 str(attrs['radiance_offsets'][ind]) +
                                 ' scale: '+str(attrs['radiance_scales'][ind]) +
                                                ' ems1km: '+str(cor[0]) +
                                                ' tcs1km: '+str(cor[1]) +
                                                ' tci1km: '+str(cor[2]) +
                                                ' min: '+str(masked_data.min()) +
                                                ' max: '+str(masked_data.max()))
                        datavars[datasettag][channame+'BT'] = masked_data
                        #  SAVE THESE AS chan31BT
                        # masked_data = data3*.01 - 230
                    if channame in\
                       corrections_ref[metadata['top']['platform_name']].\
                       keys():
                        corrected_data =\
                            np.ma.masked_equal(np.ma.array(data),
                                               attrs['_FillValue'])
                        corrected_data =\
                            np.ma.masked_greater(masked_data,
                                                 attrs['valid_range'][1])
                        corrected_data =\
                            np.ma.masked_less(masked_data,
                                              attrs['valid_range'][0])
                        offset = corrections_ref[
                            metadata['top']['platform_name']][channame][1]
                        scale = corrections_ref[
                            metadata['top']['platform_name']][channame][0]
                        corrected_data += offset
                        corrected_data *= 100.0*scale
                        log.info('    Adding channame: '+str(channame+'Ref') +
                                 ' offset: '+str(offset)+' scale: '+str(scale))
                        datavars[datasettag][channame+'Ref'] = corrected_data
        return


def parse_metadata(metadatadict):
    metadata = {}
    for ii in metadatadict.keys():
        # metadata passed by reference - add to it in subroutines.
        if ii == 'CoreMetadata.0':
            parse_core_metadata(metadata, metadatadict['CoreMetadata.0'])
        elif ii == 'ArchiveMetadata.0':
            parse_archive_metadata(metadata, metadatadict['ArchiveMetadata.0'])
        elif ii == 'StructMetadata.0':
            parse_struct_metadata(metadata, metadatadict['StructMetadata.0'])
        else:
            metadata[ii] = metadatadict[ii]
    return metadata


def parse_struct_metadata(metadata, metadatastr):
    pass


def parse_core_metadata(metadata, metadatastr):
    ii = 0
    lines = metadatastr.split('\n')
    # The HDF4 structure is stored as a big text string in
    # ArchiveMetadata.0, StructMetadata.0, and CoreMetadata.0
    # dictionary entries.  Parsing out the values we need from
    # CoreMetadata.0
    for line in lines:
        # We want to skip END_OBJECT, and only match OBJECT tags. So put a ' '
        # in front of OBJECT Get the value 2 lines past the opening tag
        # (that is the actual value) Remove white space and "s

        # Lines like:
        # '      OBJECT                 = ASSOCIATEDINSTRUMENTSHORTNAME'
        # Skip anything that does not fit that format
        try:
            [typ, field] = [piece.strip() for piece in line.split('=')]
        except:
            ii += 1
            continue
        for currval in ['RANGEENDINGDATE', 'RANGEBEGINNINGDATE',
                        'DAYNIGHTFLAG', 'SHORTNAME']:
            if 'OBJECT' == typ and currval == field:
                metadata[currval] = lines[ii+2].split('=')[1].\
                        replace('"', '').strip()

        # Also remove the trailing .0000000 from times.
        for currval in ['RANGEBEGINNINGTIME', 'RANGEENDINGTIME']:
            if 'OBJECT' == typ and " = "+currval in line:
                metadata[currval] = lines[ii+2].split('=')[1].strip().\
                        replace('"', '').split('.')[0]

        # These have 'CLASS' in addition to 'NUMVAL' between OBJECT and VALUE.
        # So have to do ii+3
        for currval in ['ASSOCIATEDSENSORSHORTNAME',
                        'ASSOCIATEDPLATFORMSHORTNAME']:
            if 'OBJECT' == typ and currval == field:
                metadata[currval] = lines[ii+3].split('=')[1].\
                        strip().replace('"', '')
        ii += 1


def parse_archive_metadata(metadata, metadatastr):
    lines = metadatastr.split('\n')
    ii = 0

    # The HDF4 structure is stored as a big text string in
    # ArchiveMetadata.0, StructMetadata.0, and CoreMetadata.0
    # dictionary entries.  Parsing out the values we need from
    # ArchiveMetadata.0
    for line in lines:
        for currattr in ['EASTBOUNDINGCOORDINATE', 'NORTHBOUNDINGCOORDINATE',
                         'SOUTHBOUNDINGCOORDINATE', 'WESTBOUNDINGCOORDINATE']:
            if ' OBJECT' in line and currattr in line:
                # Get the value 2 lines past the opening tag (that is the
                # actual value) Remove white space
                metadata[currattr] = lines[ii+2].split('=')[1].strip()
        ii += 1
