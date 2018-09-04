# Testing

# Python Standard Libraries
import os
import logging
from glob import glob
from struct import unpack
from datetime import datetime, timedelta
from collections import Hashable


# Installed Libraries
import numpy as np
from scipy.ndimage.interpolation import zoom
from pyresample.geometry import SwathDefinition
from pyresample.kd_tree import get_neighbour_info  # , get_sample_from_neighbour_info

try:
    import numexpr as ne
except Exception:
    print 'Failed numexpr import in scifile/readers/ahi_hsd_reader_new.py. If you need it, install it.'

try:
    from IPython import embed as shell
except Exception:
    print 'Failed IPython import in scifile/readers/ahi_hsd_reader_new.py. If you need it, install it.'

# GeoIPS Libraries
from .reader import Reader
from geoips.utils.log_setup import interactive_log_setup
from geoips.utils.plugin_paths import paths as gpaths

log = interactive_log_setup(logging.getLogger(__name__))

reader_class_name = 'AHI_HSD_Reader'
try:
    nprocs = 6
    ne.set_num_threads(nprocs)
except Exception:
    print 'Failed numexpr.set_num_threads. If numexpr is not installed and you need it, install it.'

DONT_AUTOGEN_GEOLOCATION = False
if os.getenv('DONT_AUTOGEN_GEOLOCATION'):
    DONT_AUTOGEN_GEOLOCATION = True
# CAB 20180904: Removing these to try and reduce the amount of emails we are
# getting from satuser
#GEOLOCDIR = os.path.join(gpaths['SATOPS'], 'longterm_files/geolocation/AHI')
#if os.getenv('GEOLOCDIR'):
#    GEOLOCDIR = os.path.join(os.getenv('GEOLOCDIR'), 'AHI')
#
#DYNAMIC_GEOLOCDIR = os.path.join(gpaths['SATOPS'], 'intermediate_files/geolocation/AHI')
#if os.getenv('DYNAMIC_GEOLOCDIR'):
#    DYNAMIC_GEOLOCDIR = os.path.join(os.getenv('DYNAMIC_GEOLOCDIR'), 'AHI')

READ_GEOLOCDIRS = []
if os.getenv('READ_GEOLOCDIRS'):
    READ_GEOLOCDIRS = [os.path.join(pp, 'AHI') for pp in os.getenv('READ_GEOLOCDIRS').split(':')]

# These should be added to the data file object
BADVALS = {'Off_Of_Disk': -999.9,
           'Error': -999.8,
           'Out_Of_Valid_Range': -999.7,
           'Root_Test': -999.6,
           'Unitialized': -9999.9}


class AutoGenError(Exception):
    pass


def findDiff(d1, d2, path=""):
    for k in d1.keys():
        if k not in d2:
            print path, ':'
            print k + " as key not in d2", "\n"
        else:
            if type(d1[k]) is dict:
                if path == "":
                    path = k
                else:
                    path = path + "->" + k
                findDiff(d1[k], d2[k], path)
            else:
                if np.all(d1[k] != d2[k]):
                    print path, ":"
                    print " - ", k, " : ", d1[k]
                    print " + ", k, " : ", d2[k]


def metadata_to_datetime(metadata):
    '''
    Use information from block_01 to get the image datetime.
    '''
    ost = metadata['block_01']['ob_start_time']
    otl = metadata['block_01']['ob_timeline']
    dt = datetime(1858, 11, 17, 00, 00, 00)
    dt += timedelta(days=np.floor(ost))
    dt += timedelta(hours=int(otl // 100), minutes=int(otl % 100))
    return dt


def _get_geolocation_metadata(metadata):
    '''
    Gather all of the metadata used in creating geolocation data for the input filename.
    This is split out so we can easily create a hash of the data for creation of a unique filename.
    This allows us to avoid recalculation of angles that have already been calculated.
    '''
    geomet = {}
    geomet['ob_area'] = metadata['block_01']['ob_area']
    geomet['num_lines'] = int(metadata['block_02']['num_lines'] * metadata['block_07']['num_segments'])
    geomet['num_samples'] = int(metadata['block_02']['num_samples'])
    geomet['lfac'] = float(metadata['block_03']['LFAC'])
    geomet['loff'] = float(metadata['block_03']['LOFF'])
    geomet['cfac'] = float(metadata['block_03']['CFAC'])
    geomet['coff'] = float(metadata['block_03']['COFF'])
    geomet['Rs'] = float(metadata['block_03']['earth_to_sat_radius'])
    geomet['Sd_coeff'] = float(metadata['block_03']['Sd_coeff'])
    geomet['ecc'] = float(metadata['block_03']['r3'])
    geomet['sub_lon'] = float(metadata['block_03']['sub_lon'])
    return geomet


def get_latitude_longitude(metadata):
    '''
    This routine accepts a dictionary containing metadata as read from an HSD format file
    and returns latitudes and longitudes for a full disk image.

    Note: This code has been adapted from Dan Lindsey's Fortran90 code.  This was done in three steps
    that ultimately culminated in faster, but more difficult to understand code.  If you plan to edit
    this, I recommend that you return to Dan's original code, then explore the commented code here,
    then finally, look at the single-command statements that are currently being used.
    '''
    # If the filename format needs to change for the pre-generated geolocation
    # files, please discuss prior to changing.  It will force recreation of all
    # files, which can be problematic for large numbers of sectors
    fname = get_geolocation_cache_filename('GEOLL', metadata)
    if not os.path.isfile(fname):
        if DONT_AUTOGEN_GEOLOCATION:
            msg = ('GETGEO Requested NO AUTOGEN GEOLOCATION. ' +
                   'Could not create latlonfile for ad {}: {}').format(metadata['ob_area'], fname)
            log.error(msg)
            raise AutoGenError(msg)

        log.debug('Calculating latitudes and longitudes.')

        sclunit = 1.525878906250000e-05  # NOQA

        # Constants
        log.info('    LATLONCALC Building constants.')
        pi = np.pi
        rad2deg = 180.0 / pi  # NOQA
        deg2rad = pi / 180.0  # NOQA
        num_lines = metadata['num_lines']
        num_samples = metadata['num_samples']
        lfac = metadata['lfac']  # NOQA
        loff = metadata['loff']  # NOQA
        cfac = metadata['cfac']  # NOQA
        coff = metadata['coff']  # NOQA
        Rs = metadata['Rs']  # NOQA
        Sd_coeff = metadata['Sd_coeff']  # NOQA
        ecc = metadata['ecc']  # NOQA
        sub_lon = metadata['sub_lon']  # NOQA

        # first_line = df.metadata['block_07']['segment_first_line'][0]
        first_line = 0
        # last_line = first_line + num_lines
        last_line = num_lines
        line_step = 1

        first_sample = 0
        last_sample = num_samples
        sample_step = 1

        # Create cartesian grid
        log.info('    LATLONCALC Creating cartesian grid')
        x, y = np.meshgrid(np.arange(first_sample, last_sample, sample_step),
                           np.arange(first_line, last_line, line_step))
        # Changing to use numexpr rather than numpy.  Appears to speed up each statement by about five times.
        #
        # In [8]: timeit -n100 deg2rad * (np.array(x, dtype=np.float) - coff)/(sclunit * cfac)
        # 100 loops, best of 3: 96.6 ms per loop
        #
        # In [9]: timeit -n100 ne.evaluate('deg2rad*(x-coff)/(sclunit*cfac)')
        # 100 loops, best of 3: 20 ms per loop
        x = ne.evaluate('deg2rad * (x - coff) / (sclunit * cfac)')  # NOQA
        y = ne.evaluate('deg2rad*(y - loff)/(sclunit * lfac)')  # NOQA
        # # Improvement here is from 132ms for np.sin(x) to 23.5ms for ne.evaluate('sin(x)')
        log.info('    LATLONCALC Calculating sines and cosines')
        # sin_x = ne.evaluate('sin(x)')  # NOQA
        # sin_y = ne.evaluate('sin(y)')  # NOQA
        # cos_x = ne.evaluate('cos(x)')  # NOQA
        # cos_y = ne.evaluate('cos(y)')  # NOQA

        # Calculate surface distance (I think)
        # Improvement here is from 200ms for numpy to 16.9ms for ne
        log.debug('Calculating Sd')
        Sd = ne.evaluate('(Rs * cos(x) * cos(y))**2 - (cos(y)**2 + ecc * sin(y)**2) * Sd_coeff')
        # No real savings on these lines.  Leave alone.
        Sd[Sd < 0.0] = 0.0
        Sd **= 0.5

        # # Good data mask
        # good = Sd != 0

        # # Now I'm lost, but it seems to work.  Comes from the Himawari-8 users's guide.
        # # Original version with excess calculations
        log.debug('Calculating Sn')
        # Sn = ne.evaluate('(Rs * cos_x * cos_y-Sd)/(cos_y**2 + ecc * sin_y**2)')  # NOQA
        log.debug('Calculating S1')
        # S1 = ne.evaluate('Rs - (Sn * cos_x * cos_y)')  # NOQA
        log.debug('Calculating S2')
        # S2 = ne.evaluate('Sn * sin_x * cos_y')  # NOQA
        log.debug('Calculating S3')
        # S3 = ne.evaluate('-Sn * sin_y')  # NOQA
        log.debug('Calculating Sxy')
        # Sxy = ne.evaluate('(S1**2 + S2**2)**0.5')  # NOQA

        # # if hasattr(self, '_temp_latitudes_arr'):
        # #     lats = self._temp_latitudes_arr
        # # else:
        log.debug('    LATLONCALC Allocating latitudes')
        # lats = np.full((num_lines, num_samples), df.BADVALS['Off_Of_Disk'])
        # # if hasattr(self, '_temp_longitudes_arr'):
        # #     lons = self._temp_longitudes_arr
        # # else:
        log.debug('    LATLONCALC Allocating longitudes')
        # lons = np.full((num_lines, num_samples), df.BADVALS['Off_Of_Disk'])

        # # It may help to figure out how to index into an array in numeval
        # # Improves from 663ms for numpy to 329ms for numeval
        # log.debug('Calculating latitudes')
        # lats[good] = ne.evaluate('rad2deg*arctan(ecc*S3/Sxy)')[good]
        # # Improves from 669ms for numpy to 301ms for numeval
        # log.debug('Calculating longitudes')
        # lons[good] = ne.evaluate('rad2deg*arctan(S2/S1)+sub_lon')[good]
        # # No real savings on these lines.  Leave alone.
        # lons[lons > 180.0] -= 360
        # # self._latitudes = lats
        # # self._longitudes = lons

        # The following equations have been combined from above.
        # The more we can fit into a single equation, the faster things will be.
        # I know this makes things ugly, but hopefully this will never have to be edited.
        log.info('    LATLONCALC Calculating latitudes')
        bad = Sd == 0
        lats = ne.evaluate('rad2deg*arctan(-ecc*(Rs*cos(x)*cos(y)-Sd)/(cos(y)**2+ecc*sin(y)**2) * sin(y)' +
                           '/ ((Rs-(Rs*cos(x)*cos(y)-Sd)/(cos(y)**2+ecc*sin(y)**2)*cos(x)*cos(y))**2'
                           '+ ((Rs*cos(x)*cos(y)-Sd)/(cos(y)**2+ecc*sin(y)**2)*sin(x)*cos(y))**2)**0.5)')
        lats[bad] = BADVALS['Off_Of_Disk']
        log.info('    LATLONCALC Calculating longitudes')
        lons = ne.evaluate('rad2deg*arctan(((Rs*cos(x)*cos(y)-Sd)/(cos(y)**2 + ecc*sin(y)**2))*sin(x)*cos(y)' +
                           '/ (Rs-((Rs*cos(x)*cos(y)-Sd)/(cos(y)**2 + ecc*sin(y)**2))*cos(x)*cos(y))) + sub_lon')
        lons[bad] = BADVALS['Off_Of_Disk']
        lons[lons > 180.0] -= 360
        log.debug('Done calculating latitudes and longitudes')

        with open(fname, 'w') as df:
            lats.tofile(df)
            lons.tofile(df)

    # Create a memmap to the lat/lon file
    # Nothing will be read until explicitly requested
    # We are mapping this here so that the lats and lons are available when calculating satlelite angles
    log.info('GETGEO memmap to {} : lat/lon file for {}'.format(fname, metadata['ob_area']))
    shape = (metadata['num_lines'], metadata['num_samples'])
    offset = 8 * metadata['num_samples'] * metadata['num_lines']
    lats = np.memmap(fname, mode='r', dtype=np.float64, offset=0, shape=shape)
    lons = np.memmap(fname, mode='r', dtype=np.float64, offset=offset, shape=shape)

    return lats, lons


def get_satellite_angles(metadata, lats, lons):

    # If the filename format needs to change for the pre-generated geolocation
    # files, please discuss prior to changing.  It will force recreation of all
    # files, which can be problematic for large numbers of sectors
    fname = get_geolocation_cache_filename('GEOSAT', metadata)
    if not os.path.isfile(fname):
        if DONT_AUTOGEN_GEOLOCATION:
            msg = ('GETGEO Requested NO AUTOGEN GEOLOCATION. ' +
                   'Could not create sat_file for ad {}: {}').format(metadata['ob_area'], fname)
            log.error(msg)
            raise AutoGenError(msg)

        log.debug('Calculating satellite zenith and azimuth angles.')
        pi = np.pi
        deg2rad = pi / 180.0  # NOQA
        rad2deg = 180.0 / pi  # NOQA
        sub_lat = 0.0  # NOQA
        sub_lon = metadata['sub_lon']  # NOQA
        sat_alt = metadata['Rs']  # NOQA
        num_lines = metadata['num_lines']  # NOQA
        num_samples = metadata['num_samples']  # NOQA

        # Convert lats/lons to radians from sub point
        log.info('    SATCALC Calculating beta')
        beta = ne.evaluate('arccos(cos(deg2rad * (lats - sub_lat)) * cos(deg2rad * (lons - sub_lon)))')  # NOQA

        bad = lats == BADVALS['Off_Of_Disk']

        # Calculate satellite zenith angle
        log.info('    SATCALC Calculating satellite zenith angle')
        zen = ne.evaluate('sat_alt * sin(beta) / sqrt(1.808e9 - 5.3725e8 * cos(beta))')
        # Where statements take the place of np.clip(zen, -1.0, 1.0)
        ne.evaluate('rad2deg * arcsin(where(zen < -1.0, -1.0, where(zen > 1.0, 1.0, zen)))', out=zen)
        zen[bad] = BADVALS['Off_Of_Disk']

        # Sat azimuth
        log.info('    SATCALC Calculating satellite azimuth angle')
        azm = ne.evaluate('sin(deg2rad * (lons - sub_lon)) / sin(beta)')
        ne.evaluate('rad2deg * arcsin(where(azm < -1.0, -1.0, where(azm > 1.0, 1.0, azm)))', out=azm)
        ne.evaluate('where(lats < sub_lat, 180.0-azm, azm)', out=azm)
        ne.evaluate('where(azm < 0.0, 360.0 + azm, azm)', out=azm)
        azm[bad] = BADVALS['Off_Of_Disk']

        log.debug('Done calculating satellite zenith and azimuth angles')

        with open(fname, 'w') as df:
            zen.tofile(df)
            azm.tofile(df)

    # Create a memmap to the lat/lon file
    # Nothing will be read until explicitly requested
    # We are mapping this here so that the lats and lons are available when calculating satlelite angles
    log.info('GETGEO memmap to {} : lat/lon file for {}'.format(fname, metadata['ob_area']))
    shape = (metadata['num_lines'], metadata['num_samples'])
    offset = 8 * metadata['num_samples'] * metadata['num_lines']
    zen = np.memmap(fname, mode='r', dtype=np.float64, offset=0, shape=shape)
    azm = np.memmap(fname, mode='r', dtype=np.float64, offset=offset, shape=shape)

    return zen, azm


def get_indexes(metadata, lats, lons, sect):
    '''
    Return two 2-D arrays containing the X and Y indexes that should be used from the raw data
    for the input sector definition.
    '''
    # The get_neighbor_info function returns three four arrays:
    #    valid_input_index: a 1D boolean array indicating where the source lats and lons
    #                       are valid values (not masked)
    #    valid_output_index: a 1D boolean array indicating where the sector lats and lons
    #                        are valid values (always true everywhere)
    #    index_array: a 1D array of ints indicating which indicies in the flattened inputs
    #                 should be used to fit the sector lats and lons
    #    distance_array: Distances from the source point for each found point.
    #
    # What we do here is feed our data lats/lons to get_neighbour_info.
    # We then reshape valid_input_index to fit our lats/lons and find the 2D indicies where
    #   the input lats and lons were good.
    # We then subset the "good" indicies with index_array to retrieve the required indicies for
    #   the sector.
    # This is complicated because get_neighbour_info does not report the indicies of the
    #   input data, but instead reports the indicies of the flattened data where valid_input_index
    #   is True
    # Get filename for sector indicies


    # If the filename format needs to change for the pre-generated geolocation
    # files, please discuss prior to changing.  It will force recreation of all
    # files, which can be problematic for large numbers of sectors
    #fname = get_geolocation_cache_filename('GEOINDS', metadata, sect)
    fname = get_geolocation_cache_filename('GEOLL', metadata, sect)

    if not os.path.isfile(fname):
        if DONT_AUTOGEN_GEOLOCATION:
            msg = ('GETGEO Requested NO AUTOGEN GEOLOCATION. ' +
                   'Could not create inds_file {} for {}').format(fname, sect.name)
            log.error(msg)
            raise AutoGenError(msg)
        # Allocate the full disk area definition
        log.info('    GETGEOINDS Creating full disk swath definition for {}'.format(sect.name))
        fldk_ad = SwathDefinition(np.ma.masked_less(lons, -999.1), np.ma.masked_less(lats, -999.1))
        ad = sect.area_definition

        # Radius of influence will be 10 times the nominal spatial resolution of the data
        #   in meters
        # This uses the only piece of information available concerning resolution in the metadata
        log.info('    GETGEOINDS Calculating radius of influence {}'.format(sect.name))
        roi = 10000 * np.ceil(2.0 * 40000000.0 / metadata['cfac']) / 2.0
        log.info('    GETGEOINDS Running get_neighbour_info {}'.format(sect.name))
        valid_input_index, valid_output_index, index_array, distance_array = \
            get_neighbour_info(fldk_ad, ad, radius_of_influence=roi, neighbours=1, nprocs=nprocs)
        log.info('    GETGEOINDS Getting good lines and samples {}'.format(sect.name))
        good_lines, good_samples = np.where(valid_input_index.reshape(lats.shape))
        log.info('    GETGEOINDS Reshaping lines and samples {}'.format(sect.name))
        # When get_neighbour_info does not find a good value for a specific location it
        #   fills index_array with the maximum index + 1.  So, just throw away all of the
        #   out of range indexes.
        index_mask = (index_array == len(good_lines))
        # good_index_array = index_array[np.where(index_array != len(good_lines))]
        lines = np.empty(ad.size, dtype=np.int64)
        lines[index_mask] = -999.1
        lines[~index_mask] = good_lines[index_array[~index_mask]]
        samples = np.empty(ad.size, dtype=np.int64)
        samples[index_mask] = -999.1
        samples[~index_mask] = good_samples[index_array[~index_mask]]

        log.info('    GETGEOINDS Writing to {} : inds_file for {}'.format(fname, sect.name))
        # Store indicies for sector
        with open(str(fname), 'w') as df:
            lines.tofile(df)
            samples.tofile(df)

    # Create a memmap to the lat/lon file
    # Nothing will be read until explicitly requested
    # We are mapping this here so that the lats and lons are available when calculating satlelite angles
    log.info('GETGEO memmap to {} : inds file for {}'.format(fname, metadata['ob_area']))
    shape = sect.area_definition.shape
    offset = 8 * shape[0] * shape[1]
    lines = np.memmap(fname, mode='r', dtype=np.int64, offset=0, shape=shape)
    samples = np.memmap(fname, mode='r', dtype=np.int64, offset=offset, shape=shape)

    return lines, samples


def calculate_solar_angles(metadata, lats, lons, dt):
    # If debug is set to True, memory savings will be turned off in order to keep
    # all calculated results for inspection.
    # If set to False, variables will attempt to reuse memory when possible which
    # will result in some results being overwritten when no longer needed.
    debug = False

    log.debug('Calculating solar zenith and azimuth angles.')

    # Getting good value mask
    # good = lats > -999
    # good_lats = lats[good]
    # good_lons = lons[good]

    # Constants
    pi = np.pi
    pi2 = 2 * pi  # NOQA
    num_lines = metadata['num_lines']
    num_samples = metadata['num_samples']
    shape = (num_lines, num_samples)  # NOQA
    size = num_lines * num_samples  # NOQA
    deg2rad = pi / 180.0  # NOQA
    rad2deg = 180.0 / pi  # NOQA

    # Calculate any non-data dependent quantities
    jday = float(dt.strftime('%j'))
    a1 = (1.00554 * jday - 6.28306) * (pi / 180.0)
    a2 = (1.93946 * jday - 23.35089) * (pi / 180.0)
    et = -7.67825 * np.sin(a1) - 10.09176 * np.sin(a2)  # NOQA

    # Solar declination radians
    log.debug('Calculating delta')
    delta = deg2rad * 23.4856 * np.sin(np.deg2rad(0.9683 * jday - 78.00878))  # NOQA

    # Pre-generate sin and cos of latitude
    log.debug('Calculating sin and cos')
    sin_lat = np.sin(deg2rad * lats)  # NOQA
    cos_lat = np.cos(deg2rad * lats)  # NOQA

    # Hour angle
    log.debug('Initializing hour angle')
    solar_time = dt.hour + dt.minute / 60.0 + dt.second / 3600.0  # NOQA
    h_ang = ne.evaluate('deg2rad*((solar_time + lons / 15.0 + et / 60.0 - 12.0) * 15.0)')

    # Pre-allocate all required arrays
    # This avoids having to allocate them again every time the generator is accessed
    log.debug('Allocating arrays')
    sun_elev = np.empty_like(h_ang)

    # Hour angle at all points in radians
    log.debug('Calculating hour angle')

    # Sun elevation
    log.debug('Calculating sun elevation angle using sin and cos')
    ne.evaluate('arcsin(sin_lat * sin(delta) + cos_lat * cos(delta) * cos(h_ang))', out=sun_elev)  # NOQA

    log.debug('Calculating caz')
    # No longer need sin_lat and this saves 3.7GB
    if not debug:
        caz = sin_lat
    else:
        caz = np.empty_like(sin_lat)
    ne.evaluate('-cos_lat * sin(delta) + sin_lat * cos(delta) * cos(h_ang) / cos(sun_elev)', out=caz)  # NOQA

    log.debug('Calculating az')
    # No longer need h_ang and this saves 3.7GB
    if not debug:
        az = h_ang
    else:
        az = np.empty_like(h_ang)
    ne.evaluate('cos(delta)*sin(h_ang)/cos(sun_elev)', out=az)  # NOQA
    # No longer need sin_lat and this saves 3.7GB
    if not debug:
        sun_azm = cos_lat
    else:
        sun_azm = np.empty_like(cos_lat)
    ne.evaluate('where(az <= -1, -pi/2.0, where(az > 1, pi/2.0, arcsin(az)))', out=sun_azm)

    log.debug('Calculating solar zenith angle')
    # No longer need sun_elev and this saves 3.7GB RAM
    if not debug:
        sun_zen = sun_elev
    else:
        sun_zen = np.empty_like(sun_elev)
    ne.evaluate('90.0-rad2deg*sun_elev', out=sun_zen)

    log.debug('Calculating solar azimuth angle')
    ne.evaluate('where(caz <= 0, pi - sun_azm, where(az <= 0, 2.0 * pi + sun_azm, sun_azm))', out=sun_azm)
    sun_azm += pi
    ne.evaluate('where(sun_azm > 2.0 * pi, sun_azm - 2.0 * pi, sun_azm)', out=sun_azm)
    # ne.evaluate('where(caz <= 0, pi - sun_azm, sun_azm) + pi', out=sun_azm)
    # ne.evaluate('rad2deg * where(sun_azm < 0, sun_azm + pi2, where(sun_azm >= pi2, sun_azm - pi2, sun_azm))',
    #             out=sun_azm)
    log.debug('Done calculating solar zenith and azimuth angles')

    return sun_zen, sun_azm


def get_geolocation_cache_filename(pref, metadata, sect=None):
    '''
    Set the location and filename format for the pre-generated cached geolocation 
    files.
    There is a separate filename format for satellite lat lons and sector lat lons
    If the filename format needs to change for the pre-generated geolocation
    files, please discuss prior to changing.  It will force recreation of all
    files, which can be problematic for large numbers of sectors
    '''
    cache = GEOLOCDIR
    if sect and sect.isdynamic:
        cache = DYNAMIC_GEOLOCDIR
    if not os.path.isdir(cache):
        os.makedirs(cache)

    md_hash = hash(frozenset((k, v) for k, v in metadata.items() if isinstance(v, Hashable)))
    #md_hash = hash(frozenset(metadata.items()))


    fname = "{}_{}_{}x{}".format(pref,
                                    metadata['ob_area'],
                                    metadata['num_lines'],
                                    metadata['num_samples']
                                    )

    # If the filename format needs to change for the pre-generated geolocation
    # files, please discuss prior to changing.  It will force recreation of all
    # files, which can be problematic for large numbers of sectors

    if sect:
        ad = sect.area_definition
        log.info('    Using area_definition information for hash: '+str(ad.proj_dict.items()))
        sector_hash = hash(frozenset(ad.proj_dict.items()))
        sect_nlines = ad.shape[0]
        sect_nsamples = ad.shape[1]
        sect_clat = sect.area_info.center_lat_float
        sect_clon = sect.area_info.center_lon_float
        fname += '_{}_{}x{}_{}x{}'.format(sect.name,
            sect_nlines,
            sect_nsamples,
            sect_clat,
            sect_clon)
        fname += "_{}_{}".format(md_hash, sector_hash)
    else:
        fname += "_{}".format(md_hash)

    fname += '.DAT'

    # Check alternative read-only directories (i.e. operational)
    for dirname in READ_GEOLOCDIRS:
        if os.path.exists(os.path.join(dirname, fname)):
            return os.path.join(dirname, fname)

    # If not found, return the normal cached filename
    return os.path.join(cache, fname)


def get_geolocation(dt, metadata, sect=None):
    '''
    Gather and return the geolocation data for the input metadata.
    Input metadata should be the metadata for a single AHI data file.

    If latitude/longitude have not been calculated with the metadata from the input datafile
    they will be recalculated and stored for future use.  They shouldn't change often.
    No matter which segment's metadata are used, the entire domain's worth of lats and lons will
    be calculated, then subset for the requested sector.  This means that the first time this is
    called after a metadata update it will be slow, but will be fast thereafter.

    The same is true for satellite zenith and azimuth angles.

    Solar zenith and azimuth angles are always calculated on the fly.
    This is because they actually change.
    This may be slow for full-disk images.
    '''
    adname = 'None'
    if sect:
        adname = sect.name
    # Get just the metadata we need
    gmd = _get_geolocation_metadata(metadata)

    try:
        fldk_lats, fldk_lons = get_latitude_longitude(gmd)
        fldk_sat_zen, fldk_sat_azm = get_satellite_angles(gmd, fldk_lats, fldk_lons)
    except AutoGenError:
        return False

    # Determine which indicies will be needed for the sector if there is one.
    if sect is not None:
        try:
            lines, samples = get_indexes(gmd, fldk_lats, fldk_lons, sect)
        except AutoGenError:
            return False

        # Get lats, lons, and satellite zenigh and azimuth angles for required points
        # This may not be entirely appropriate, especially if we want to do something better than
        # nearest neighbor interpolation.
        shape = sect.area_definition.shape
        index_mask = (lines != -999.1)

        lons = np.full(shape, -999.1)
        lats = np.full(shape, -999.1)
        sat_zen = np.full(shape, -999.1)
        sat_azm = np.full(shape, -999.1)

        lons[index_mask] = fldk_lons[lines[index_mask], samples[index_mask]]
        lats[index_mask] = fldk_lats[lines[index_mask], samples[index_mask]]
        sat_zen[index_mask] = fldk_sat_zen[lines[index_mask], samples[index_mask]]
        sat_azm[index_mask] = fldk_sat_azm[lines[index_mask], samples[index_mask]]

    else:
        lats = fldk_lats
        lons = fldk_lons
        sat_zen = fldk_sat_zen
        sat_azm = fldk_sat_azm

    # Get generator for solar zenith and azimuth angles
    log.info('GETGEO Must calculate solar zen/azm for sector {}'.format(adname))
    sun_zen, sun_azm = calculate_solar_angles(gmd, lats, lons, dt)
    log.info('GETGEO Done calculating solar zen/azm for sector {}'.format(adname))
    sun_zen = np.ma.masked_less_equal(sun_zen, -999.1)
    sun_azm = np.ma.masked_less_equal(sun_azm, -999.1)

    geolocation = {'Latitude': np.ma.masked_less_equal(lats, -999.1),
                   'Longitude': np.ma.masked_less_equal(lons, -999.1),
                   'SatZenith': np.ma.masked_less_equal(sat_zen, -999.1),
                   'SatAzimuth': np.ma.masked_less_equal(sat_azm, -999.1),
                   'SunZenith': np.ma.masked_less_equal(sun_zen, -999.1),
                   'SunAzimuth': np.ma.masked_less_equal(sun_azm, -999.1)}

    try:
        geolocation['Lines'] = np.array(lines)
        geolocation['Samples'] = np.array(samples)
    except NameError:
        pass

    return geolocation


def _get_metadata_block_info(df):
    '''
    Returns a dictionary whose keys represent metadata block numbers and whose values are tuples
    containing the block's starting byte number and the block's length in bytes.
    '''
    # Initialize the first block's data
    block_info = {1: (0, 0)}

    # Loop over blocks and determine their sizes
    for blockind in range(1, 12):
        # Make sure we are at the start of the block
        block_start = block_info[blockind][0]
        df.seek(block_start)

        # Read the block number and block length
        block_num = unpack('B', df.read(1))[0]
        if block_num != blockind:
            raise IOError('Unexpected block number encountered.  Expected %s, but got %s.' %
                          (blockind, block_num))
        block_length = unpack('H', df.read(2))[0]

        # Add block_length for the current block
        block_info[blockind] = (block_start, block_length)

        # Add entry for the NEXT block
        if blockind < 11:
            block_info[blockind + 1] = (block_start + block_length, 0)

    return block_info


def _get_metadata_block_01(df, block_info):
    '''
    Parse the first metadata block from an AHI data file and return a dictionary containing
    that metadata.
    '''
    # Get the block start and length in bytes
    block_start, block_length = block_info[1]

    # Seek to the start of the block and read the block in its entirety
    df.seek(block_start)
    data = df.read(block_length)

    # Create dictionary for this block
    block_data = {}
    block_data['block_name'] = 'basic_information'
    block_data['block_num'] = np.fromstring(data[0], dtype='uint8')[0]
    block_data['block_length'] = np.fromstring(data[1:3], dtype='uint16')[0]
    block_data['num_headers'] = np.fromstring(data[3:5], dtype='uint16')[0]
    block_data['byte_order'] = np.fromstring(data[5], dtype='uint8')[0]
    block_data['satellite_name'] = data[6:22].replace('\x00', '')
    block_data['processing_center'] = data[22:38].replace('\x00', '')
    block_data['ob_area'] = data[38:42].replace('\x00', '')
    block_data['other_ob_info'] = data[42:44].replace('\x00', '')
    block_data['ob_timeline'] = np.fromstring(data[44:46], dtype='uint16')[0]
    block_data['ob_start_time'] = np.fromstring(data[46:54], dtype='float64')[0]
    block_data['ob_end_time'] = np.fromstring(data[54:62], dtype='float64')[0]
    block_data['creation_time'] = np.fromstring(data[62:70], dtype='float64')[0]
    block_data['total_header_length'] = np.fromstring(data[70:74], dtype='uint32')[0]
    block_data['total_data_length'] = np.fromstring(data[74:78], dtype='uint32')[0]
    block_data['quality_flag_1'] = np.fromstring(data[78], dtype='uint8')[0]
    block_data['quality_flag_2'] = np.fromstring(data[79], dtype='uint8')[0]
    block_data['quality_flag_3'] = np.fromstring(data[80], dtype='uint8')[0]
    block_data['quality_flag_4'] = np.fromstring(data[81], dtype='uint8')[0]
    block_data['file_format_version'] = data[82:114].replace('\x00', '')
    block_data['file_name'] = data[114:242].replace('\x00', '')
    block_data['spare'] = data[242:282].replace('\x00', '')

    return block_data


def _get_metadata_block_02(df, block_info):
    '''
    Parse the second metadata block from an AHI data file and return a dictionary containing
    that metadata.
    '''
    # Get the block start and length in bytes
    block_start, block_length = block_info[2]

    # Seek to the start of the block and read the block in its entirety
    df.seek(block_start)
    data = df.read(block_length)

    # Create dictionary for this block
    block_data = {}
    block_data['block_name'] = 'data_information'
    block_data['block_num'] = np.fromstring(data[0], dtype='uint8')[0]
    block_data['block_length'] = np.fromstring(data[1:3], dtype='uint16')[0]
    block_data['bits_per_pixel'] = np.fromstring(data[3:5], dtype='uint16')[0]
    block_data['num_samples'] = np.fromstring(data[5:7], dtype='uint16')[0]
    block_data['num_lines'] = np.fromstring(data[7:9], dtype='uint16')[0]
    block_data['compression_flag'] = np.fromstring(data[9], dtype='uint8')[0]
    block_data['spare'] = data[10:50].replace('\x00', '')

    return block_data


def _get_metadata_block_03(df, block_info):
    '''
    Parse the third metadata block from an AHI data file and return a dictionary containing
    that metadata.
    '''
    # Get the block start and length in bytes
    block_start, block_length = block_info[3]

    # Seek to the start of the block and read the block in its entirety
    df.seek(block_start)
    data = df.read(block_length)

    # Create dictionary for this block
    block_data = {}
    block_data['block_name'] = 'projection_information'
    block_data['block_num'] = np.fromstring(data[0], dtype='uint8')[0]
    block_data['block_length'] = np.fromstring(data[1:3], dtype='uint16')[0]
    block_data['sub_lon'] = np.fromstring(data[3:11], dtype='float64')[0]
    # Column sclaing factor
    block_data['CFAC'] = np.fromstring(data[11:15], dtype='uint32')[0]
    # Line scaling factor
    block_data['LFAC'] = np.fromstring(data[15:19], dtype='uint32')[0]
    # Column offset
    block_data['COFF'] = np.fromstring(data[19:23], dtype='float32')[0]
    # Line offset
    block_data['LOFF'] = np.fromstring(data[23:27], dtype='float32')[0]
    # Distance to earth's center
    block_data['earth_to_sat_radius'] = np.fromstring(data[27:35], dtype='float64')[0]
    # Radius of earth at equator
    block_data['equator_radius'] = np.fromstring(data[35:43], dtype='float64')[0]
    # Radius of earth at pole
    block_data['pole_radius'] = np.fromstring(data[43:51], dtype='float64')[0]
    # (R_eq**2 - R_pol**2)/R_eq**2
    block_data['r1'] = np.fromstring(data[51:59], dtype='float64')[0]
    # R_pol**2/R_eq**2
    block_data['r2'] = np.fromstring(data[59:67], dtype='float64')[0]
    # R_eq**2/R_pol**2
    block_data['r3'] = np.fromstring(data[67:75], dtype='float64')[0]
    # Coefficient for S_d(R_s**2 - R_eq**2)
    block_data['Sd_coeff'] = np.fromstring(data[75:83], dtype='float64')[0]
    block_data['resampling_types'] = np.fromstring(data[83:85], dtype='uint16')[0]
    block_data['resampling_size'] = np.fromstring(data[85:87], dtype='uint16')[0]
    block_data['spare'] = np.fromstring(data[87:127], dtype='uint16')

    return block_data


def _get_metadata_block_04(df, block_info):
    '''
    Parse the third metadata block from an AHI data file and return a dictionary containing
    that metadata.
    '''
    # Get the block start and length in bytes
    block_start, block_length = block_info[4]

    # Seek to the start of the block and read the block in its entirety
    df.seek(block_start)
    data = df.read(block_length)

    # Create dictionary for this block
    block_data = {}
    block_data['block_name'] = 'navigation_information'
    block_data['block_num'] = np.fromstring(data[0], dtype='uint8')[0]
    block_data['block_length'] = np.fromstring(data[1:3], dtype='uint16')[0]
    block_data['nav_info_time'] = np.fromstring(data[3:11], dtype='float64')[0]
    block_data['SSP_lon'] = np.fromstring(data[11:19], dtype='float64')[0]
    block_data['SSP_lat'] = np.fromstring(data[19:27], dtype='float64')[0]
    block_data['earthcenter_to_sat_dist'] = np.fromstring(data[27:35], dtype='float64')[0]
    block_data['nadir_lon'] = np.fromstring(data[35:43], dtype='float64')[0]
    block_data['nadir_lat'] = np.fromstring(data[43:51], dtype='float64')[0]
    block_data['sun_pos'] = np.fromstring(data[51:75], dtype='float64')
    block_data['moon_pos'] = np.fromstring(data[75:99], dtype='float64')
    block_data['spare'] = np.fromstring(data[99:139], dtype='float64')

    return block_data


def _get_metadata_block_05(df, block_info):
    '''
    Parse the third metadata block from an AHI data file and return a dictionary containing
    that metadata.
    '''
    # Get the block start and length in bytes
    block_start, block_length = block_info[5]

    # Seek to the start of the block and read the block in its entirety
    df.seek(block_start)
    data = df.read(block_length)

    # Create dictionary for this block
    block_data = {}
    block_data['block_name'] = 'calibration_information'
    block_data['block_num'] = np.fromstring(data[0], dtype='uint8')[0]
    block_data['block_length'] = np.fromstring(data[1:3], dtype='uint16')[0]
    block_data['band_number'] = np.fromstring(data[3:5], dtype='uint16')[0]
    block_data['cent_wavelenth'] = np.fromstring(data[5:13], dtype='float64')[0]
    block_data['valid_bits_per_pixel'] = np.fromstring(data[13:15], dtype='uint16')[0]
    block_data['count_badval'] = np.fromstring(data[15:17], dtype='uint16')[0]
    block_data['count_outside_scan'] = np.fromstring(data[17:19], dtype='uint16')[0]
    block_data['gain'] = np.fromstring(data[19:27], dtype='float64')[0]
    block_data['offset'] = np.fromstring(data[27:35], dtype='float64')[0]
    if block_data['band_number'] in range(7, 17):
        block_data['c0'] = np.fromstring(data[35:43], dtype='float64')[0]
        block_data['c1'] = np.fromstring(data[43:51], dtype='float64')[0]
        block_data['c2'] = np.fromstring(data[51:59], dtype='float64')[0]
        block_data['C0'] = np.fromstring(data[59:67], dtype='float64')[0]
        block_data['C1'] = np.fromstring(data[67:75], dtype='float64')[0]
        block_data['C2'] = np.fromstring(data[75:83], dtype='float64')[0]
        block_data['speed_of_light'] = np.fromstring(data[83:91], dtype='float64')[0]
        block_data['planck_const'] = np.fromstring(data[91:99], dtype='float64')[0]
        block_data['boltz_const'] = np.fromstring(data[99:107], dtype='float64')[0]
        # block_data['spare'] = np.fromstring(data[107:147], dtype='float64')
    else:
        block_data['c_prime'] = np.fromstring(data[35:43], dtype='float64')[0]
        block_data['spare'] = np.fromstring(data[43:147], dtype='float64')

    return block_data


def _get_metadata_block_06(df, block_info):
    '''
    Parse the third metadata block from an AHI data file and return a dictionary containing
    that metadata.
    '''
    # Get the block start and length in bytes
    block_start, block_length = block_info[6]

    # Seek to the start of the block and read the block in its entirety
    df.seek(block_start)
    data = df.read(block_length)

    # Create dictionary for this block
    block_data = {}
    block_data['block_name'] = 'intercalibration_information'
    block_data['block_num'] = np.fromstring(data[0], dtype='uint8')[0]
    block_data['block_length'] = np.fromstring(data[1:3], dtype='uint16')[0]
    # Global Space-based Inter-Calibration System (GSICS) calibration coefficients
    block_data['GSICS_intercept'] = np.fromstring(data[3:11], dtype='float64')[0]
    block_data['GSICS_slope'] = np.fromstring(data[11:19], dtype='float64')[0]
    block_data['GSICS_quadratic'] = np.fromstring(data[19:27], dtype='float64')[0]
    block_data['radiance_bias'] = np.fromstring(data[27:35], dtype='float64')[0]
    block_data['bias_uncert'] = np.fromstring(data[35:43], dtype='float64')[0]
    block_data['standard_radiance'] = np.fromstring(data[43:51], dtype='float64')[0]
    block_data['GSICS_valid_start'] = np.fromstring(data[51:59], dtype='float64')[0]
    block_data['GSICS_valid_end'] = np.fromstring(data[59:67], dtype='float64')[0]
    block_data['GSICS_upper_limit'] = np.fromstring(data[67:71], dtype='float32')[0]
    block_data['GSICS_lower_limit'] = np.fromstring(data[71:75], dtype='float32')[0]
    block_data['GSICS_filename'] = data[75:203].replace('\x00', '')
    block_data['spare'] = data[203:259].replace('\x00', '')

    return block_data


def _get_metadata_block_07(df, block_info):
    '''
    Parse the third metadata block from an AHI data file and return a dictionary containing
    that metadata.
    '''
    # Get the block start and length in bytes
    block_start, block_length = block_info[7]

    # Seek to the start of the block and read the block in its entirety
    df.seek(block_start)
    data = df.read(block_length)

    # Create dictionary for this block
    block_data = {}
    block_data['block_name'] = 'segment_information'
    block_data['block_num'] = np.fromstring(data[0], dtype='uint8')[0]
    block_data['block_length'] = np.fromstring(data[1:3], dtype='uint16')[0]
    block_data['num_segments'] = np.fromstring(data[3], dtype='uint8')[0]
    block_data['segment_number'] = np.fromstring(data[4], dtype='uint8')[0]
    block_data['segment_first_line'] = np.fromstring(data[5:7], dtype='uint16')[0]
    block_data['spare'] = data[7:47].replace('\x00', '')

    return block_data


def _get_metadata_block_08(df, block_info):
    '''
    Parse the third metadata block from an AHI data file and return a dictionary containing
    that metadata.
    '''
    # Get the block start and length in bytes
    block_start, block_length = block_info[8]

    # Seek to the start of the block and read the block in its entirety
    df.seek(block_start)
    data = df.read(block_length)

    # Create dictionary for this block
    block_data = {}
    block_data['block_name'] = 'navigation_correction_information'
    block_data['block_num'] = np.fromstring(data[0], dtype='uint8')[0]
    block_data['block_length'] = np.fromstring(data[1:3], dtype='uint16')[0]
    block_data['center_scan_of_rotation'] = np.fromstring(data[3:7], dtype='float32')[0]
    block_data['center_line_of_rotation'] = np.fromstring(data[7:11], dtype='float32')[0]
    block_data['rotation_correction'] = np.fromstring(data[11:19], dtype='float64')[0]
    block_data['num_correction_info'] = np.fromstring(data[19:21], dtype='uint16')[0]

    start = 21
    block_data['line_num_after_rotation'] = np.empty(block_data['num_correction_info'])
    block_data['scan_shift_amount'] = np.empty(block_data['num_correction_info'])
    block_data['line_shift_amount'] = np.empty(block_data['num_correction_info'])
    for info_ind in range(0, block_data['num_correction_info']):
        block_data['line_num_after_rotation'][info_ind] = np.fromstring(data[start:start + 2], dtype='uint16')
        block_data['scan_shift_amount'][info_ind] = np.fromstring(data[start + 2:start + 6], dtype='float32')
        block_data['line_shift_amount'][info_ind] = np.fromstring(data[start + 6:start + 10], dtype='float32')
        start += 10
    block_data['spare'] = data[start:start + 40].replace('\x00', '')

    return block_data


def _get_metadata_block_09(df, block_info):
    '''
    Parse the third metadata block from an AHI data file and return a dictionary containing
    that metadata.
    '''
    # Get the block start and length in bytes
    block_start, block_length = block_info[9]

    # Seek to the start of the block and read the block in its entirety
    df.seek(block_start)
    data = df.read(block_length)

    # Create dictionary for this block
    block_data = {}
    block_data['block_name'] = 'observation_time_information'
    block_data['block_num'] = np.fromstring(data[0], dtype='uint8')[0]
    block_data['block_length'] = np.fromstring(data[1:3], dtype='uint16')[0]
    block_data['num_ob_times'] = np.fromstring(data[3:5], dtype='uint16')[0]

    start = 5
    block_data['ob_time_line_number'] = np.empty(block_data['num_ob_times'])
    block_data['ob_time'] = np.empty(block_data['num_ob_times'])
    for info_ind in range(0, block_data['num_ob_times']):
        block_data['ob_time_line_number'][info_ind] = np.fromstring(data[start:start + 2], dtype='uint16')
        block_data['ob_time'][info_ind] = np.fromstring(data[start + 2:start + 10], dtype='float64')
        start += 10
    block_data['spare'] = data[start:start + 40].replace('\x00', '')

    return block_data


def _get_metadata_block_10(df, block_info):
    '''
    Parse the third metadata block from an AHI data file and return a dictionary containing
    that metadata.
    '''
    # Get the block start and length in bytes
    block_start, block_length = block_info[10]

    # Seek to the start of the block and read the block in its entirety
    df.seek(block_start)
    data = df.read(block_length)

    # Create dictionary for this block
    block_data = {}
    block_data['block_name'] = 'error_information'
    block_data['block_num'] = np.fromstring(data[0], dtype='uint8')[0]
    block_data['block_length'] = np.fromstring(data[1:3], dtype='uint16')[0]
    block_data['num_err_info_data'] = np.fromstring(data[3:5], dtype='uint16')[0]

    start = 5
    block_data['err_line_number'] = np.array([])
    block_data['num_err_per_line'] = np.array([])
    for info_ind in range(0, block_data['num_err_info_data']):
        block_data['err_line_number'].append(np.fromstring(data[start:start + 2], dtype='uint16'))
        block_data['num_err_per_line'].append(np.fromstring(data[start + 2:start + 4], dtype='uint16'))
        start += 4
    block_data['spare'] = data[start:start + 40].replace('\x00', '')

    return block_data


def _get_metadata_block_11(df, block_info):
    '''
    Parse the third metadata block from an AHI data file and return a dictionary containing
    that metadata.
    '''
    # Get the block start and length in bytes
    block_start, block_length = block_info[11]

    # Seek to the start of the block and read the block in its entirety
    df.seek(block_start)
    data = df.read(block_length)

    # Create dictionary for this block
    block_data = {}
    block_data['block_name'] = 'spare'
    block_data['block_num'] = np.fromstring(data[0], dtype='uint8')[0]
    block_data['block_length'] = np.fromstring(data[1:3], dtype='uint16')[0]
    block_data['spare'] = data[3:259].replace('\x00', '')

    return block_data


def _get_metadata(df, **kwargs):
    '''
    Gather metadata for the data file and return as a dictionary.
    '''
    metadata = {}
    # Get metadata block info
    block_info = _get_metadata_block_info(df)

    # Read all 12 blocks
    metadata['block_01'] = _get_metadata_block_01(df, block_info)
    metadata['block_02'] = _get_metadata_block_02(df, block_info)
    metadata['block_03'] = _get_metadata_block_03(df, block_info)
    metadata['block_04'] = _get_metadata_block_04(df, block_info)
    metadata['block_05'] = _get_metadata_block_05(df, block_info)
    metadata['block_06'] = _get_metadata_block_06(df, block_info)
    metadata['block_07'] = _get_metadata_block_07(df, block_info)
    metadata['block_08'] = _get_metadata_block_08(df, block_info)
    metadata['block_09'] = _get_metadata_block_09(df, block_info)
    metadata['block_10'] = _get_metadata_block_10(df, block_info)
    metadata['block_11'] = _get_metadata_block_11(df, block_info)
    # Gather some useful info to the top level
    metadata['path'] = df.name
    # metadata['satellite'] = metadata['block_01']['satellite_name']
    metadata['satellite'] = metadata['block_01']['satellite_name']
    # Can this be gotten from the data?
    metadata['sensor'] = 'AHI'
    # Make accessable to parent classes that don't know the structure of our metadata
    metadata['num_lines'] = metadata['block_02']['num_lines']
    metadata['num_samples'] = metadata['block_02']['num_samples']
    return metadata


def _get_files(path):
    '''
    Get a list of file names from the input path.
    '''
    if os.path.isfile(path):
        fnames = [path]
    elif os.path.isdir(path):
        # Temporarily only looking for full disk images.
        # Should change later.
        fnames = glob(path + '/*.DAT')
    else:
        raise IOError('No such file or directory: {0}'.format(path))
    return fnames


def _check_file_consistency(metadata):
    '''
    Checks to be sure that all input metadata are from the same image time.
    Performs checks on ob_start_time (date only), ob_timeline, ob_area, and sub_lon.
    If these are all equal, returns True.
    If any differ, returns False.
    '''
    # Checks start dates without comparing times.
    # Times are uncomparable using this field, but are compared below using ob_timeline.
    start_dates = [int(metadata[fname]['block_01']['ob_start_time']) for fname in metadata.keys()]
    if start_dates[1:] != start_dates[:-1]:
        return False

    # Check the following fields for exact equality.
    #   satellite_name: Must make sure this isn't Himawari-8 and 9 mixed.
    #   ob_timeline: Provides HHMM for each image, so should be the same for all files from thes same image.
    #   ob_area: Provides the four letter code of the observation area (e.g. FLDK or JP01).
    #   sub_lon: Just a dummy check to be sure nothing REALLY weird is going on.
    members_to_check = {'block_01': {'satellite_name': None, 'ob_timeline': None, 'ob_area': None},
                        'block_03': {'sub_lon': None}
                        }

    for block in members_to_check.keys():
        for field in members_to_check[block].keys():
            member_vals = [metadata[fname][block][field] for fname in metadata.keys()]
            # This tests to be sure that all elemnts in member_vals are equal
            # If they aren't all equal, then return False
            if member_vals[1:] != member_vals[:-1]:
                return False
    return True


def sort_by_band_and_seg(metadata):
    # cfac = metadata['block_03']['CFAC']
    band_number = metadata['block_05']['band_number']
    segment_number = metadata['block_07']['segment_number']
    # return '{0}_{1:02d}_{2:02d}'.format(cfac, band_number, segment_number)
    return '{0:02d}_{1:02d}'.format(band_number, segment_number)


class AHI_HSD_Reader(Reader):

    dataset_info = {'LOW': ['B05', 'B06', 'B07', 'B08', 'B09', 'B10', 'B11', 'B12', 'B13', 'B14', 'B15', 'B16'],
                    'MED': ['B01', 'B02', 'B04'],
                    'HIGH': ['B03']
                    }
    all_chans = {'LOW': ['B05Rad', 'B05Ref',   # 1.61um
                         'B06Rad', 'B06Ref',   # 2.267um
                         'B07Rad', 'B07BT',    # 3.8853um
                         'B08Rad', 'B08BT',    # 6.2429um
                         'B09Rad', 'B09BT',    # 6.9410um
                         'B10Rad', 'B10BT',    # 7.3467um
                         'B11Rad', 'B11BT',    # 8.5926um
                         'B12Rad', 'B12BT',    # 9.6372um
                         'B13Rad', 'B13BT',    # 10.4073um
                         'B14Rad', 'B14BT',    # 11.2395um
                         'B15Rad', 'B15BT',    # 12.3806um
                         'B16Rad', 'B16BT'],   # 13.2807um
                 'MED': ['B01Rad', 'B01Ref',   # 0.47063um
                         'B02Rad', 'B02Ref',   # 0.51000um
                         'B04Rad', 'B04Ref'],  # 0.85670um
                 'HIGH': ['B03Rad', 'B03Ref']  # 0.63914um
                 }

    @staticmethod
    def format_test(path):
        # Currently only allows unzipped HSD files.
        # Should probably allow BZ2 files, too
        # Does handle directories of files

        # Handle single file
        fnames = _get_files(path)

        # If there are no HS_*.DAT files, fnames will be []
        # Obviously that is not valid.
        if not fnames:
            return False

        # Check that all files are HSD
        from ..file_format_tests import hsd_format_test
        for fname in fnames:
            if not hsd_format_test(fname):
                return False
        return True

    def read(self, path, datavars, gvars, scifile_metadata, chans=None, sector_definition=None,
             self_register=False):
        # Get a list of files in the path
        # If path is a regular file, will just contain path
        fnames = _get_files(path)
        adname = 'undefined'
        if sector_definition and self_register:
            raise ValueError('sector_definition and self_register are mutually exclusive keywords')
        elif sector_definition:
            adname = sector_definition.name
        elif self_register:
            if self_register not in self.dataset_info:
                raise ValueError('Unrecognized resolution name requested for self registration: {}'.format(
                    self_register))
            adname = 'FULL_DISK'

        # Get metadata for all input data files
        all_metadata = {fname: _get_metadata(open(fname, 'r')) for fname in fnames}

        # Check to be sure that all input files are from the same image time
        if not _check_file_consistency(all_metadata):
            raise ValueError('Input files inconsistent.')

        # Now put together a dict that shows what we actually got
        # This is largely to help us read in order and only create arrays of the minimum required size
        # Dict structure is channel{segment{file}}
        # Also build sets containing all segments and channels passed
        file_info = {}
        file_segs = set()
        file_chans = set()
        for md in all_metadata.values():
            ch = 'B{0:02d}'.format(md['block_05']['band_number'])
            sn = md['block_07']['segment_number']
            if ch not in file_info:
                file_info[ch] = {}
            file_info[ch][sn] = md
            file_segs.add(sn)
            file_chans.add(ch)

        # Most of the metadata are the same between files.
        # From here on we will just rely on the metadata from a single data file for each resolution.
        res_md = {}
        for res in ['HIGH', 'MED', 'LOW']:
            # Find a file file for this resolution: Any one will do
            res_chans = list(set(self.dataset_info[res]).intersection(file_info.keys()))
            if res_chans:
                # Gets metadata for all available segments for this channel
                segment_info = file_info[res_chans[0]]
                # Get the metadata for any of the segments (doesn't matter which)
                res_md[res] = segment_info[segment_info.keys()[0]]

        # If we plan to self register, make sure we requested a resolution that we actually plan to read
        if self_register and self_register not in res_md:
            raise ValueError('Resolution requested for self registration has not been read.')

        # Gather metadata
        # Assume the same for all resolutions.   Not true, but close enough.
        highest_md = res_md[res_md.keys()[0]]
        dt = metadata_to_datetime(highest_md)  # Assume same for all
        ob_area = highest_md['block_01']['ob_area']
        if ob_area == 'FLDK':
            scifile_metadata['top']['sector_name'] = 'Full-Disk'
        elif ob_area[0:2] == 'JP':
            scifile_metadata['top']['sector_name'] = 'Japan-{}'.format(ob_area[2:])
        elif ob_area[0] == 'R':
            scifile_metadata['top']['sector_name'] = 'Regional-{}-{}'.format(ob_area[1], ob_area[2:])
        else:
            raise ValueError('Unregognized ob_area {}'.format(ob_area))
        scifile_metadata['top']['start_datetime'] = dt
        scifile_metadata['top']['source_name'] = 'ahi'
        scifile_metadata['top']['platform_name'] = highest_md['block_01']['satellite_name'].replace('-', '').lower()
        scifile_metadata['top']['sector_definition'] = sector_definition

        # Tells process that we DO NOT need to composite granules of this data type (save I/O)
        scifile_metadata['top']['NO_GRANULE_COMPOSITES'] = True
        # Tells driver to read this data only a sector at a time
        scifile_metadata['top']['SECTOR_ON_READ'] = True

        # If an empty list of channels was requested, just stop here and output the metadata
        if chans == []:
            return

        # If one or more channels are missing a segment that other channels have, add it in as "None"
        # This will be set to bad values in the output data
        for ch, segs in file_info.items():
            diff = file_segs.difference(segs.keys())
            if diff:
                segs.update({(sn, None) for sn in diff})

        all_chans_list = []
        for chl in self.all_chans.values():
            all_chans_list += chl

        # If specific channels were requested, check them against input data
        # If specific channels were requested, but no files exist for one of the channels, then error
        if chans:
            for chan in chans:
                if chan not in all_chans_list:
                    raise ValueError('Requested channel {0} not recognized.'.format(chan))
                if chan[0:3] not in file_chans:
                    raise ValueError('Requested channel {0} not found in input data'.format(chan))

        # If no specific channels were requested, get everything
        if not chans:
            chans = all_chans_list
        # Creates dict whose keys are band numbers in the form B## and whose values are lists
        # containing the data type(s) requested for the band (e.g. Rad, Ref, BT).
        chan_info = {}
        for ch in chans:
            chn = ch[0:3]
            typ = ch[3:]
            if chn not in chan_info:
                chan_info[chn] = []
            chan_info[chn].append(typ)

        # Gather geolocation data
        # Assume datetime the same for all resolutions.  Not true, but close enough.
        # This saves us from having very slightly different solar angles for each channel.
        # Loop over resolutions and get metadata as needed
        # for res in ['HIGH', 'MED', 'LOW']:
        if self_register:
            log.info('')
            log.interactive('Getting geolocation information for resolution {} for {}.'.format(res, adname))
            gvars[adname] = get_geolocation(dt, res_md[self_register], sector_definition)
            if not gvars[adname]:
                log.error('GEOLOCATION FAILED for {} resolution {} DONT_AUTOGEN_GEOLOCATION is: {}'.format(
                    adname, res, DONT_AUTOGEN_GEOLOCATION))
                gvars[res] = {}
        else:
            for res in ['HIGH', 'MED', 'LOW']:
                try:
                    res_md[res]
                except KeyError:
                    continue
                log.info('')
                log.interactive('Getting geolocation information for resolution {} for {}'.format(res, adname))
                gvars[res] = get_geolocation(dt, res_md[res], sector_definition)
                if not gvars[res]:
                    log.error('GEOLOCATION FAILED for {} resolution {} DONT_AUTOGEN_GEOLOCATION is: {}'.format(
                        adname, res, DONT_AUTOGEN_GEOLOCATION))
                    gvars[res] = {}

        log.info('Done with geolocation for {}'.format(adname))
        log.info('')
        # Read the data
        # Will read all data if sector_definition is None
        # Will only read required data if an sector_definition is provided
        for chan, types in chan_info.items():
            log.info('Reading {}'.format(chan))
            chan_md = file_info[chan]
            for res, res_chans in self.dataset_info.items():
                if chan in res_chans:
                    break
            if (not self_register) and (res not in gvars.keys() or not gvars[res]):
                log.interactive("We don't have geolocation information for {} for {} skipping {}".format(
                    res, adname, chan))
                continue
            if not sector_definition:
                dsname = res
            else:
                dsname = adname

            rad = ref = bt = False
            if 'Rad' in types:
                rad = True
            if 'Ref' in types:
                ref = True
            if 'BT' in types:
                bt = True
            # zoom = 1
            # if self_register:
            #     if self_register == 'HIGH':
            #         if res == 'MED':
            #             zoom = 2
            #         if res == 'LOW':
            #             zoom = 4
            #     elif self_register == 'MED':
            #         if res == 'HIGH':
            #             zoom = 0.5
            #         if res == 'LOW':
            #             zoom = 2
            #     else:
            #         if res == 'HIGH':
            #             zoom = 0.25
            #         if res == 'MID':
            #             zoom = 0.5

            # Need to think about how to implement "zoom" to read only what is needed.
            # This is more complicated than I thought initially.
            # Mostly due to problems with ensuring that zoom produces integer dimensions
            #   and is an integer itself when inverted.
            # data = self.get_data(chan_md, gvars[res], rad, ref, bt, zoom=zoom)
            data = self.get_data(chan_md, gvars[res], rad, ref, bt)
            for typ, val in data.items():
                if dsname not in datavars:
                    datavars[dsname] = {}
                datavars[dsname][chan + typ] = val

        # This needs to be fixed:
        #   remove any unneeded datasets from datavars and gvars
        #   also mask any values below -999.0
        if sector_definition:
            for res in ['HIGH', 'MED', 'LOW']:
                if adname not in gvars:
                    gvars[adname] = gvars[res]
                gvars.pop(res)

        if self_register:
            adname = 'FULL_DISK'

            # Determine which resolution has geolocation
            log.info('Registering to {}'.format(self_register))
            if self_register == 'HIGH':
                datavars['FULL_DISK'] = datavars.pop('HIGH')
                for varname, var in datavars['LOW'].items():
                    datavars['FULL_DISK'][varname] = zoom(var, 4, order=0)
                datavars.pop('LOW')
                for varname, var in datavars['MED'].items():
                    datavars['FULL_DISK'][varname] = zoom(var, 2, order=0)
                datavars.pop('MED')

            elif self_register == 'MED':
                datavars['FULL_DISK'] = datavars.pop('MED')
                for varname, var in datavars['LOW'].items():
                    datavars['FULL_DISK'][varname] = zoom(var, 2, order=0)
                datavars.pop('LOW')
                for varname, var in datavars['HIGH'].items():
                    datavars['FULL_DISK'][varname] = var[::2, ::2]
                datavars.pop('HIGH')

            elif self_register == 'LOW':
                datavars['FULL_DISK'] = datavars.pop('LOW')
                for varname, var in datavars['MED'].items():
                    datavars['FULL_DISK'][varname] = var[::2, ::2]
                datavars.pop('MED')
                for varname, var in datavars['HIGH'].items():
                    datavars['FULL_DISK'][varname] = var[::4, ::4]
                datavars.pop('HIGH')

            else:
                raise ValueError('No geolocation data found.')

        # Remove lines and samples arrays.  Not needed.
        for res in gvars.keys():
            try:
                gvars[res].pop('Lines')
                gvars[res].pop('Samples')
            except KeyError:
                pass
        for ds in datavars.keys():
            if not datavars[ds]:
                datavars.pop(ds)
            else:
                for varname in datavars[ds].keys():
                    datavars[ds][varname] = np.ma.masked_less(datavars[ds][varname], -999.1)
        log.info('Done reading AHI data for {}'.format(adname))
        log.info('')
        return

    @staticmethod
    def get_data(md, gvars, rad=False, ref=False, bt=False, zoom=1.0):
        '''
        Read data for a full channel's worth of files.
        '''
        # Coordinate arrays for reading
        # Unsure if Lines can ever be None, but the test below was causing an error due to testing
        #   the truth value of an entire array.  May need to implement test again here to ensure that
        #   gvars['Lines'] is actually something, but testing this method for now.
        # Test against full-disk.  Works for sectors...
        # if ('Lines' in gvars and 'Samples' in gvars) and gvars['Lines'].any() and gvars['Samples'].any():
        if 'Lines' in gvars and 'Samples' in gvars:
            full_disk = False
            line_inds = gvars['Lines']
            sample_inds = gvars['Samples']
            shape = line_inds.shape

            # All required line numbers (used for determining which files to even look at)
            req_lines = set(line_inds.flatten())
        else:
            full_disk = True
            # Assume we are going to make a full-disk image
            smd = md[md.keys()[0]]
            nseg = smd['block_07']['num_segments']
            lines = smd['num_lines'] * nseg
            samples = smd['num_samples']
            # sample_inds, line_inds = np.meshgrid(np.arange(samples), np.arange(lines))
            shape = (lines, samples)

            # # Determine dimension sizes
            # lines = []
            # samples = []
            # shell()
            # for seg, smd in md.items():
            #     lines.append(smd['num_lines'])
            #     samples.append(smd['num_samples'])
            # # Sum the nubmer of lines per segment
            # lines = np.sum(lines)
            # # Samples must be the same for all segments
            # samples = set(samples)
            # if len(samples) != 1:
            #     raise ValueError('Number of samples per segment do not match.')
            # samples = list(samples)[0]

            # sample_inds, line_inds = np.meshgrid(np.arange(samples), np.arange(lines))
            # line_inds = line_inds.astype('int32')
            # sample_inds = sample_inds.astype('int32')

            req_lines = set(range(lines))

        # Initialize empty array for channel
        valid_bits = md[md.keys()[0]]['block_05']['valid_bits_per_pixel']
        # # Ensure zoom produces an integer result
        # zoom_mod = np.mod(np.array(shape), 1/zoom)
        # if np.any(zoom_mod):
        #     raise ValueError('Zoom level does not produce integer dimensions.')
        # counts = np.full(np.int(np.array(shape) * zoom), 1 + 2**valid_bits, dtype=np.uint16)
        log.debug('Making counts array')
        counts = np.full(shape, 1 + 2**valid_bits, dtype=np.uint16)

        # Loop over segments
        for seg, smd in md.items():
            log.info('Reading segment {}'.format(seg))
            # Skip if we don't have a file for this segment
            if not smd:
                continue

            # Get calibration info
            log.debug('Getting calibration info')
            calib = smd['block_05']
            gain = calib['gain']
            offset = calib['offset']
            count_badval = calib['count_badval']
            count_outbounds = calib['count_outside_scan']
            valid_bits = smd['block_05']['valid_bits_per_pixel']

            # Get info for current file
            log.debug('Getting lines and samples')
            path = smd['path']
            nl = smd['num_lines']
            ns = smd['num_samples']
            first_line = smd['block_07']['segment_first_line']
            lines = range(first_line, first_line + nl)

            # If required lines and file lines don't intersect, move on to the next file
            if not req_lines.intersection(lines):
                continue

            log.debug('Determining indicies in data array.')
            header_len = smd['block_01']['total_header_length']
            if not full_disk:
                data_inds = np.where((line_inds >= first_line) & (line_inds < first_line + nl))
                data_lines = line_inds[data_inds] - first_line
                data_samples = sample_inds[data_inds]
                counts[data_inds] = np.memmap(path, mode='r', dtype=np.uint16,
                                              offset=header_len, shape=(nl, ns))[data_lines, data_samples]
            else:
                first_line -= 1
                last_line = first_line + nl
                counts[first_line:last_line, :] = np.memmap(path, mode='r', dtype=np.uint16,
                                                            offset=header_len, shape=(nl, ns))[:, :]

            log.info('Doing the actual read for segment {}'.format(seg))

        # It appears that there are values that appear to be good outside the allowable range
        # The allowable range is set by the number of valid bits per pixel
        # This number can be 11, 12, or 14
        # These correspond to valid ranges of [0:2048], [0:4096], [0:16384]
        # Here we find all invalid pixels so we can mask later
        outrange_inds = np.where(((counts < 0) | (counts > 2**valid_bits)))
        error_inds = np.where(counts == count_badval)
        offdisk_inds = np.where(counts == count_outbounds)

        # It appears that some AHI data does not correctly set erroneous pixels to count_badval.
        # To fis this, we can find the count value at which radiances become less than or equal to zero.
        # Any counts above that value are bad.
        # Note: This is only for use when calculating brightness temperatures (i.e. when gain is negative)
        if gain < 0:
            root = -offset / gain
            root_inds = np.where(counts > root)
        else:
            root_inds = []

        # Create mask for good values in order to suppress warning from log of negative values.
        # Note: This is only for use when calculating brightness temperatures
        good = np.ones(counts.shape, dtype=np.bool)
        good[root_inds] = 0
        good[outrange_inds] = 0
        good[error_inds] = 0
        good[offdisk_inds] = 0

        # Create data dict
        data = {}

        # Convert to radiances
        data['Rad'] = counts * gain + offset

        # If reflectance is requested
        # Note the weird memory manipulation to save memory when radiances are not requested
        band_num = calib['band_number']
        if ref:
            log.info('Converting to Reflectance')
            if band_num not in range(1, 7):
                raise ValueError('Unable to calculate reflectances for band #{0}'.format(band_num))

            # Get the radiance data
            # Have to do this when using ne
            rad_data = data['Rad']  # NOQA

            # If we don't need radiances, then reuse the memory
            if not rad:
                data['Ref'] = data.pop('Rad')
            else:
                data['Ref'] = np.empty_like(data['Rad'])

            c_prime = calib['c_prime']  # NOQA
            ne.evaluate('rad_data * c_prime', out=data['Ref'])

        # If brightness temperature is requested
        # Note the weird memory manipulation to save memory when radiances are not requested
        if bt:
            log.info('Converting to Brightness Temperature')
            if band_num not in range(7, 17):
                raise ValueError('Unable to calculate brightness temperatures for band #{0}'.format(band_num))

            # Get the radiance data
            # Have to do this when using ne
            rad_data = data['Rad']  # NOQA

            # If we don't need radiances, then reuse the memory
            if not rad:
                data['BT'] = data.pop('Rad')
            else:
                data['BT'] = np.empty_like(data['Rad'])

            h = calib['planck_const']
            k = calib['boltz_const']
            wl = calib['cent_wavelenth'] / 1000000.0  # Initially in microns
            c = calib['speed_of_light']
            c0 = calib['c0']  # NOQA
            c1 = calib['c1']  # NOQA
            c2 = calib['c2']  # NOQA

            # Make this as in-place as possible
            # Note, rad_data are in units of W/(m**2 sr um)
            log_coeff = (2.0 * h * c**2) / (wl**5)  # NOQA
            dividend = (h * c) / (k * wl)  # NOQA
            ne.evaluate('dividend/log( (log_coeff/(rad_data*1000000.0))+1 )', out=data['BT'])

        for val in data.values():
            log.info('Setting badvals')
            val[root_inds] = BADVALS['Root_Test']
            val[outrange_inds] = BADVALS['Out_Of_Valid_Range']
            val[offdisk_inds] = BADVALS['Off_Of_Disk']
            val[error_inds] = BADVALS['Error']

        return data
