# Python Standard Libraries
import logging
import os
from glob import glob
from datetime import datetime, timedelta
from collections import Hashable

from scipy.ndimage.interpolation import zoom
from pyresample.geometry import SwathDefinition
from pyresample.kd_tree import get_neighbour_info

from IPython import embed as shell

# Installed Libraries
try:
    # If this reader is not installed on the system, don't fail alltogether, just skip this import.  This reader
    # will not work if the import fails and the package will have to be installed to process data of this type.
    import netCDF4 as ncdf
except Exception:
    print 'Failed import netCDF4 in scifile/readers/abi_ncdf4_reader.py. If you need it, install it.'
import numpy as np

try:
    import numexpr as ne
except Exception:
    print 'Failed import numexpr in scifile/readers/abi_ncdf4_reader_new.py. If you need it, install it.'

# GeoIPS Libraries
from .reader import Reader
from geoips.utils.log_setup import interactive_log_setup
from geoips.utils.plugin_paths import paths as gpaths

log = interactive_log_setup(logging.getLogger(__name__))

# For now must include this string for automated importing of classes.
reader_class_name = 'ABI_NCDF4_Reader'
nprocs = 6
try:
    ne.set_num_threads(nprocs)
except Exception:
    print 'Failed numexpr.set_num_threads. If numexpr is not installed and you need it, install it.'

DONT_AUTOGEN_GEOLOCATION = False
if os.getenv('DONT_AUTOGEN_GEOLOCATION'):
    DONT_AUTOGEN_GEOLOCATION = True

GEOLOCDIR = os.path.join(gpaths['SATOPS'], 'longterm_files', 'geolocation', 'ABI')
if os.getenv('GEOLOCDIR'):
    GEOLOCDIR = os.path.join(os.getenv('GEOLOCDIR'), 'ABI')

DYNAMIC_GEOLOCDIR = os.path.join(gpaths['SATOPS'], 'intermediate_files', 'geolocation', 'ABI')
if os.getenv('DYNAMIC_GEOLOCDIR'):
    DYNAMIC_GEOLOCDIR = os.path.join(os.getenv('DYNAMIC_GEOLOCDIR'), 'ABI')

READ_GEOLOCDIRS = []
if os.getenv('READ_GEOLOCDIRS'):
    READ_GEOLOCDIRS = [os.path.join(pp, 'ABI') for pp in os.getenv('READ_GEOLOCDIRS').split(':')]

# These should be added to the data file object
BADVALS = {'Off_Of_Disk': -999.9,
           'Conditional': -999.8,
           'Out_Of_Valid_Range': -999.7,
           'No_Value': -999.6,
           'Unitialized': -9999.9}


class AutoGenError(Exception):
    pass


def metadata_to_datetime(metadata):
    '''
    Use information from the metadata to get the image datetime.
    '''
    times = metadata['var_info']['time_bounds']
    epoch = datetime(2000, 1, 1, 12, 0, 0)
    start_time = epoch + timedelta(seconds=times[0])
    end_time = epoch + timedelta(seconds=times[1])
    return start_time, end_time


def _get_files(path):
    '''
    Get a list of file names from the input path.
    '''
    if os.path.isfile(path):
        fnames = [path]
    elif os.path.isdir(path):
        fnames = glob(os.path.join(path, 'OR_ABI*.nc'))
    elif os.path.isfile(path[0]):
        fnames = path
    else:
        raise IOError('No such file or directory: {0}'.format(path))
    return fnames


def _check_file_consistency(metadata):
    '''
    Checks to be sure that all input metadata are from the same image time.
    Performs cheks on platform_ID, instrument_type, processing_level, and times.
    If these are all equal, returns True.
    If any differ, returns False.
    '''
    # Checking file-level metadata for exact equality in the following fields
    # Was failing on processing_level due to extra NASA text sometimes
    # Also fails on time_coverage_end due to deviations on the order of 0.5 seconds
    #   Probably should fashion better checks for these two.
    # checks = ['platform_ID', 'instrument_type', 'processing_level', 'timeline_id', 'scene_id',
    #           'time_coverage_start', 'time_coverage_end']
    checks = ['platform_ID', 'instrument_type', 'timeline_id', 'scene_id', 'time_coverage_start']
    for name in checks:
        check_set = set([metadata[fname]['file_info'][name] for fname in metadata.keys()])
        if len(check_set) != 1:
            log.debug('Failed on {0}. Found: {1}'.format(name, check_set))
            return False
    return True


def _get_file_metadata(df):
    '''
    Gather all of the file-level metadata
    '''
    metadata = {}
    md_names = ['id', 'dataset_name', 'naming_authority', 'institution', 'project', 'iso_series_metadata_id',
                'Conventions', 'Metadata_Conventions', 'keywords_vocabulary', 'standard_name_vocabulary',
                'title', 'summary', 'license', 'keywords', 'cdm_data_type', 'orbital_slot', 'platform_ID',
                'instrument_type', 'processing_level', 'date_created', 'production_site',
                'production_environment', 'production_data_source', 'timeline_id', 'scene_id',
                'spatial_resolution', 'time_coverage_start', 'time_coverage_end']
    metadata_dict = {'id': 'instrument_ID'}
    for name in md_names:
        try:
            if hasattr(df, name):
                metadata[name] = getattr(df, name)
            else:
                metadata[name] = getattr(df, metadata_dict[name])
        except AttributeError:
            log.info('Warning! File-level metadata field missing: {0}'.format(name))
    return metadata


def _get_variable_metadata(df):
    '''
    Gather all required variable level metadata.  Some are skipped or gathered later as needed.
    '''
    metadata = {}
    # Note: We have skipped DQF, Rad, band_wavelength_star_look, num_star_looks, star_id, t, t_star_look,
    #       x_image, x_image_bounds, y_image, y_image_bounds, geospatial_lat_lon_extent,
    #       goes_imager_projection
    md_names = ['band_id', 'band_wavelength', 'earth_sun_distance_anomaly_in_AU', 'esun',
                'kappa0', 'max_radiance_value_of_valid_pixels', 'min_radiance_value_of_valid_pixels',
                'missing_pixel_count', 'nominal_satellite_height', 'nominal_satellite_subpoint_lat',
                'nominal_satellite_subpoint_lon', 'percent_uncorrectable_L0_errors', 'planck_bc1',
                'planck_bc2', 'planck_fk1', 'planck_fk2', 'processing_parm_version_container',
                'saturated_pixel_count', 'std_dev_radiance_value_of_valid_pixels', 'time_bounds',
                'undersaturated_pixel_count', 'valid_pixel_count', 'x', 'y', 'yaw_flip_flag']
    for name in md_names:
        try:
            metadata[name] = df.variables[name][...]
            if metadata[name].size == 1:
                metadata[name] = metadata[name][()]
        except KeyError:
            log.info('Warning! Variable-level metadata field missing: {0}'.format(name))
    metadata['num_lines'] = metadata['y'].size
    metadata['num_samples'] = metadata['x'].size
    return metadata


def _get_lat_lon_extent_metadata(df):
    glle = df.variables['geospatial_lat_lon_extent']
    metadata = {}
    md_names = ['geospatial_eastbound_longitude', 'geospatial_lat_center', 'geospatial_lat_nadir',
                'geospatial_lon_center', 'geospatial_lon_nadir',
                'geospatial_northbound_latitude',
                'geospatial_southbound_latitude', 'geospatial_westbound_longitude']
    for name in md_names:
        try:
            metadata[name] = getattr(glle, name)
            if metadata[name].size == 1:
                metadata[name] = metadata[name][()]
        except AttributeError:
            log.info('Warning! Lat lon extent metadata field missing: {0}'.format(name))
    return metadata


def _get_imager_projection(df):
    gip = df.variables['goes_imager_projection']
    metadata = {}
    md_names = ['inverse_flattening', 'latitude_of_projection_origin',
                'longitude_of_projection_origin', 'perspective_point_height', 'semi_major_axis',
                'semi_minor_axis']
    for name in md_names:
        try:
            metadata[name] = getattr(gip, name)
            if metadata[name].size == 1:
                metadata[name] = metadata[name][()]
        except AttributeError:
            log.info('Warning! Lat lon extent metadata field missing: {0}'.format(name))
    metadata['grid_mapping'] = getattr(gip, 'grid_mapping_name')
    return metadata


def _get_metadata(df, fname, **kwargs):
    '''
    Gather metadata for the data file and return as a dictionary.

    Note: We are gathering all of the available metadata in case it is needed at some point.
    '''
    metadata = {}
    # Gather all file-level metadata
    metadata['file_info'] = _get_file_metadata(df)
    # Gather all variable-level metadata
    metadata['var_info'] = _get_variable_metadata(df)
    # Gather lat lon extent info
    metadata['ll_info'] = _get_lat_lon_extent_metadata(df)
    # Gather projection info
    metadata['projection'] = _get_imager_projection(df)
    # Gather some useful info to the top level
    try:
        metadata['path'] = df.filepath()
    except ValueError:
        # Without cython installed, df.filepath() does not work
        metadata['path'] = fname
    metadata['satellite'] = metadata['file_info']['platform_ID']
    metadata['sensor'] = 'ABI'
    metadata['num_lines'] = metadata['var_info']['y'].size
    metadata['num_samples'] = metadata['var_info']['x'].size
    return metadata


def _get_geolocation_metadata(metadata):
    '''
    Gather all of the metadata used in creating geolocation data for the input filename.
    This is split out so we can easily create a chash of the data for creation of a unique filename.
    This allows us to avoid recalculation of angles that have already been calculated.
    '''
    geomet = {}
    geomet['Re'] = metadata['projection']['semi_major_axis']
    geomet['Rp'] = metadata['projection']['semi_minor_axis']
    geomet['invf'] = metadata['projection']['inverse_flattening']
    geomet['e'] = 0.0818191910435
    geomet['pphgt'] = metadata['projection']['perspective_point_height']
    geomet['H'] = geomet['Re'] + geomet['pphgt']
    geomet['lat0'] = metadata['projection']['latitude_of_projection_origin']
    geomet['lon0'] = metadata['projection']['longitude_of_projection_origin']
    geomet['scene'] = metadata['file_info']['scene_id']
    # Just getting the nadir resolution in meters.  Must extract from a string.
    geomet['res'] = float(metadata['file_info']['spatial_resolution'].split()[0][0:-2])
    geomet['num_lines'] = metadata['var_info']['num_lines']
    geomet['num_samples'] = metadata['var_info']['num_samples']
    geomet['x'] = metadata['var_info']['x']
    geomet['y'] = metadata['var_info']['y']
    return geomet


def get_latitude_longitude(metadata):
    '''
    This routine accepts a dictionary containing metadata as read from a NCDF4 format file
    and returns latitudes and longitudes for a full disk.
    '''
    # If the filename format needs to change for the pre-generated geolocation
    # files, please discuss prior to changing.  It will force recreation of all
    # files, which can be problematic for large numbers of sectors
    fname = get_geolocation_cache_filename('GEOLL', metadata)
    if not os.path.isfile(fname):
        if DONT_AUTOGEN_GEOLOCATION:
            msg = ('GETGEO Requested NO AUTOGEN GEOLOCATION. ' +
                   'Could not create latlonfile for ad {}: {}').format(metadata['scene'], fname)
            log.error(msg)
            raise AutoGenError(msg)

        log.debug('Calculating latitudes and longitudes.')

        r2d = 180.0 / np.pi  # NOQA

        lambda0 = np.radians(metadata['lon0'])  # NOQA
        Re = metadata['Re']
        # invf = metadata['invf']
        Rp = metadata['Rp']
        # e = np.sqrt((1 / invf) * (2 - 1 / invf))
        H = metadata['H']
        c = H**2 - Re**2  # NOQA
        x = np.float64(metadata['x'])
        y = np.float64(metadata['y'])

        log.info('      Making {0} by {1} grid.'.format(x.size, y.size))
        # Need to transpose the latline, then repeat lonsize times
        yT = y[np.newaxis].T
        y = np.hstack([yT for num in range(x.size)])
        # Repeat lonline latsize times
        x = np.vstack([x for num in range(yT.size)])

        # Note: In this next section, we will be reusing memory space as much as possible
        #       To make this as transparent as possible, we will do all variable assignment
        #       first, then fill them
        # This method requires that all lines remain in the SAME ORDER or things will go very badly
        cosx = np.empty_like(x)
        cosy = np.empty_like(x)
        a = np.empty_like(x)
        b = np.empty_like(x)
        sinx = x  # X is not needed after the line that defines sinx
        siny = y  # Y is not needed after the line that defines siny
        rs = a
        sx = b
        sy = cosy  # sinx is not needed after the line that defines sy
        sz = cosx  # cosx is not needed after the line that defines sz
        lats = rs
        lons = sz

        log.info('      Calculating intermediate steps')
        Rrat = Re**2 / Rp ** 2  # NOQA
        ne.evaluate('cos(x)', out=cosx)  # NOQA
        ne.evaluate('cos(y)', out=cosy)  # NOQA
        ne.evaluate('sin(x)', out=sinx)  # NOQA
        ne.evaluate('sin(y)', out=siny)  # NOQA
        ne.evaluate('sinx**2 + cosx**2 * (cosy**2 + siny**2 * Rrat)', out=a)  # NOQA
        ne.evaluate('-2 * H * cosx * cosy', out=b)  # NOQA
        ne.evaluate('(-b - sqrt(b**2 - (4 * a * c))) / (2 * a)', out=rs)  # NOQA
        good_mask = np.isfinite(rs)

        ne.evaluate('rs * cosx * cosy', out=sx)  # NOQA
        ne.evaluate('rs * cosx * siny', out=sz)  # NOQA
        ne.evaluate('rs * sinx', out=sy)  # NOQA

        log.info('Calculating Latitudes')
        ne.evaluate('r2d * arctan(Rrat * sz / sqrt((H - sx)**2 + sy**2))', out=lats)
        log.info('Calculating Longitudes')
        lons = ne.evaluate('r2d * (lambda0 + arctan(sy / (H - sx)))', out=lons)
        lats[~good_mask] = BADVALS['Off_Of_Disk']
        lons[~good_mask] = BADVALS['Off_Of_Disk']
        log.info('Done calculating latitudes and longitudes')

        with open(fname, 'w') as df:
            lats.tofile(df)
            lons.tofile(df)

    # Create memmap to the lat/lon file
    # Nothing will be read until explicitly requested
    # We are mapping this here so that the lats and lons are available when calculating satlelite angles
    log.info('GETGEO memmap to {} : lat/lon file for {}'.format(fname, metadata['scene']))
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
                   'Could not create sat_file for ad {}: {}').format(metadata['scene'], fname)
            log.error(msg)
            raise AutoGenError(msg)

        log.info('Calculating satellite zenith and azimuth angles.')
        pi = np.pi
        deg2rad = pi / 180.0  # NOQA
        rad2deg = 180.0 / pi  # NOQA
        sub_lat = 0.0  # NOQA
        sub_lon = metadata['lon0']  # NOQA
        alt = metadata['H'] / 1000.0  # NOQA
        num_lines = metadata['num_lines']  # NOQA
        num_samples = metadata['num_samples']  # NOQA

        # Convert lats / lons to radians from sub point
        log.debug('Calculating beta')
        beta = ne.evaluate('arccos(cos(deg2rad * (lats - sub_lat)) * cos(deg2rad * (lons - sub_lon)))')  # NOQA

        bad = lats == BADVALS['Off_Of_Disk']

        # Calculate satellite zenith angle
        log.debug('Calculating satellite zenith angle')
        zen = ne.evaluate('alt * sin(beta) / sqrt(1.808e9 - 5.3725e8 * cos(beta))')
        # Where statements take the place of np.clip(zen, - 1.0, 1.0)
        ne.evaluate('rad2deg * arcsin(where(zen < -1.0, -1.0, where(zen > 1.0, 1.0, zen)))', out=zen)
        zen[bad] = BADVALS['Off_Of_Disk']

        # Sat azimuth
        log.debug('Calculating satellite azimuth angle')
        azm = ne.evaluate('sin(deg2rad * (lons - sub_lon)) / sin(beta)')
        ne.evaluate('rad2deg * arcsin(where(azm < -1.0, -1.0, where(azm > 1.0, 1.0, azm)))', out=azm)
        ne.evaluate('where(lats < sub_lat, 180.0 - azm, azm)', out=azm)
        ne.evaluate('where(azm < 0.0, 360.0 + azm, azm)', out=azm)
        azm[bad] = BADVALS['Off_Of_Disk']

        log.info('Done calculating satellite zenith and azimuth angles')

        with open(fname, 'w') as df:
            zen.tofile(df)
            azm.tofile(df)

    # Create a memmap to the lat/lon file
    # Nothing will be read until explicitly requested
    # We are mapping this here so that the lats and lons are available when calculating satlelite angles
    log.info('GETGEO memmap to {} : lat/lon file for {}'.format(fname, metadata['scene']))
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
    fname = get_geolocation_cache_filename('GEOINDS', metadata, sect)

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
        roi = 10000 * metadata['res']
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
    log.info('GETGEO memmap to {} : inds file for {}'.format(fname, metadata['scene']))
    log.info('GETGEO memmap to {} : lat/lon file for {}'.format(fname, metadata['scene']))
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

    log.info('Calculating solar zenith and azimuth angles.')

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
    sin_lat = ne.evaluate('sin(deg2rad * lats)')  # NOQA
    cos_lat = ne.evaluate('cos(deg2rad * lats)')  # NOQA

    # Hour angle
    log.debug('Initializing hour angle')
    solar_time = dt.hour + dt.minute / 60.0 + dt.second / 3600.0  # NOQA
    h_ang = ne.evaluate('deg2rad * ((solar_time + lons / 15.0 + et / 60.0 - 12.0) * 15.0)')

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
    ne.evaluate('cos(delta) * sin(h_ang) / cos(sun_elev)', out=az)  # NOQA
    # No longer need sin_lat and this saves 3.7GB
    if not debug:
        sun_azm = cos_lat
    else:
        sun_azm = np.empty_like(cos_lat)
    ne.evaluate('where(az <= -1, -pi / 2.0, where(az > 1, pi / 2.0, arcsin(az)))', out=sun_azm)

    log.debug('Calculating solar zenith angle')
    # No longer need sun_elev and this saves 3.7GB RAM
    if not debug:
        sun_zen = sun_elev
    else:
        sun_zen = np.empty_like(sun_elev)
    ne.evaluate('90.0 - rad2deg * sun_elev', out=sun_zen)

    log.debug('Calculating solar azimuth angle')
    ne.evaluate('where(caz <= 0, pi - sun_azm, where(az <= 0, 2.0 * pi + sun_azm, sun_azm))', out=sun_azm)
    sun_azm += pi
    ne.evaluate('where(sun_azm > 2.0 * pi, sun_azm - 2.0 * pi, sun_azm)', out=sun_azm)
    # ne.evaluate('where(caz <= 0, pi - sun_azm, sun_azm) + pi', out=sun_azm)
    # ne.evaluate('rad2deg * where(sun_azm < 0, sun_azm + pi2, where(sun_azm >= pi2, sun_azm - pi2, sun_azm))',
    #             out=sun_azm)
    log.info('Done calculating solar zenith and azimuth angles')

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

    fname = "{}_{}_{}x{}".format(pref,
                                    metadata['scene'],
                                    metadata['num_lines'],
                                    metadata['num_samples'],
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


    fname += '.dat'

    # Check alternative read-only directories (i.e. operational)
    for dirname in READ_GEOLOCDIRS:
        if os.path.exists(os.path.join(dirname, fname)):
            return os.path.join(dirname, fname)

    # If not found, return the normal cached filename
    return os.path.join(cache, fname)


def get_geolocation(dt, metadata, sect=None):
    '''
    Gather and return the geolocation data for the input metadata.
    Input metadata should be the metadata for a single ABI data file.

    If latitude/longitude have not been calculated with the metadata form the input data file
    they will be recalculated and stored for future use.  They shouldn't change often.
    This will be slow the first time it is called after a metadata update, but fast thereafter.

    The same is true for satellite zenith and azimuth angles.

    Solar zenith ang azimuth angles are always calculated on the fly.
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

    # Determine which indicies will be needed for the input sector if there is one.
    if sect is not None:
        try:
            lines, samples = get_indexes(gmd, fldk_lats, fldk_lons, sect)
        except AutoGenError:
            return False

        # Get lats, lons, and satellite zenith and azimuth angles for the required points
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

    # Make into a dict
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


class ABI_NCDF4_Reader(Reader):
    dataset_info = {'MED': ['B01', 'B03', 'B05'],
                    'HIGH': ['B02'],
                    'LOW': ['B04', 'B06', 'B07', 'B08', 'B09', 'B10', 'B11', 'B12',
                            'B13', 'B14', 'B15', 'B16']}
    all_chans = {'LOW': ['B04Rad', 'B04Ref',   # 1.37um Near-IR Cirrus
                         'B06Rad', 'B06Ref',   # 2.2um  Near-IR Cloud Particle Size
                         'B07Rad', 'B07BT',    # 3.9um  IR      Shortwave Window
                         'B08Rad', 'B08BT',    # 6.2um  IR      Mid-level tropospheric water vapor
                         'B09Rad', 'B09BT',    # 6.9um  IR      Lower-level water vapor
                         'B10Rad', 'B10BT',    # 7.3um  IR      Lower-level Water Vapor
                         'B11Rad', 'B11BT',    # 8.4um  IR      Cloud-top phase
                         'B12Rad', 'B12BT',    # 9.6um  IR      Ozone
                         'B13Rad', 'B13BT',    # 10.3um IR      Clean IR Longwave Window
                         'B14Rad', 'B14BT',    # 11.2um IR      IR Longwave window
                         'B15Rad', 'B15BT',    # 12.3um IR      Dirty Longwave Window
                         'B16Rad', 'B16BT'],   # 13.3um IR      CO2 Longwave infrared
                 'MED': ['B01Rad', 'B01Ref',   # 0.47um Vis     Blue
                         'B02Rad', 'B02Ref',   # 0.64um Vis     Red
                         'B05Rad', 'B05Ref'],  # 1.6um  Near-IR Snow/Ice
                 'HIGH': ['B03Rad', 'B03Ref']  # 0.86um Near-IR Veggie
                 }

    @staticmethod
    def format_test(path):
        # Correctly handles directories of files
        fnames = _get_files(path)

        if not fnames:
            return False

        # Check that this file is ncdf4 format
        from ..file_format_tests import ncdf4_format_test
        instrument_test = 'GOES R Series Advanced Baseline Imager'
        for fname in fnames:
            if not ncdf4_format_test(fname):
                return False
            df = ncdf.Dataset(str(fname), 'r')
            if not hasattr(df, 'instrument_type') or df.instrument_type != instrument_test:
                return False
        return True

    def read(self, path, datavars, gvars, scifile_metadata, chans=None, sector_definition=None,
             self_register=False):

        # Get a list of files in the path
        # If path is a regular file, will just contain path
        fnames = _get_files(path)

        # Test inputs
        if sector_definition and self_register:
            raise ValueError('sector_definition and self_register are mutually exclusive keywords')

        # Get metadata for all input data files
        # Check to be sure that all input files are form the same image time
        all_metadata = {fname: _get_metadata(ncdf.Dataset(str(fname), 'r'), fname) for fname in fnames}
        if not _check_file_consistency(all_metadata):
            raise ValueError('Input files inconsistent.')

        # Now put together a dict that shows what we actually got
        # This is largely to help us read in order and only create arrays of the minimum required size
        # Dict structure is channel{metadata}
        file_info = {}
        for md in all_metadata.values():
            ch = 'B{0:02d}'.format(int(md['var_info']['band_id']))
            if ch not in file_info:
                file_info[ch] = md

        # Most of the metadata are the same between files.
        # From here on we will just rely on the metadata from a single data file for each resolution
        res_md = {}
        for res in ['HIGH', 'MED', 'LOW']:
            # Find a file for this resolution: Any one will do
            res_chans = list(set(self.dataset_info[res]).intersection(file_info.keys()))
            if res_chans:
                res_md[res] = file_info[res_chans[0]]

        # If we plan to self register, make sure we requested a resolution that we actually plan to read
        # This could be problematic if we try to self-register to LOW when only reading MED or something
        if self_register and self_register not in res_md:
            raise ValueError('Resolution requested for self registration has not been read.')

        # Gather metadata
        # Assume the same for all resolutions.  Not true, but close enough.
        highest_md = res_md[res_md.keys()[0]]
        sdt, edt = metadata_to_datetime(highest_md)
        scifile_metadata['top']['start_datetime'] = sdt
        # scifile_metadata['top']['end_datetime'] = edt
        scifile_metadata['top']['source_name'] = 'abi'

        # G16 -> goes16
        scifile_metadata['top']['platform_name'] = highest_md['file_info']['platform_ID'].replace('G', 'goes')
        scifile_metadata['top']['sector_definition'] = sector_definition

        # Tells process that we DO NOT need to composite granules of this data type (save I/O)
        scifile_metadata['top']['NO_GRANULE_COMPOSITES'] = True
        # Tells driver to read this data only a sector at a time
        scifile_metadata['top']['SECTOR_ON_READ'] = True

        # Get appropriate sector name
        if sector_definition:
            scifile_metadata['top']['sector_name'] = sector_definition.name
            scifile_metadata['top']['sector_definition'] = sector_definition
        else:
            if self_register and self_register not in self.dataset_info:
                raise ValueError('Unrecognized resolution name requested for self registration: {}'.format(
                    self_register))
            scene_id = highest_md['file_info']['dataset_name'].split('_')[1].split('-')[2]
            if scene_id == 'RadF':
                scifile_metadata['top']['sector_name'] = 'Full-Disk'
            elif scene_id == 'RadM1':
                scifile_metadata['top']['sector_name'] = 'Mesoscale-1'
            elif scene_id == 'RadM2':
                scifile_metadata['top']['sector_name'] = 'Mesoscale-2'
            elif scene_id == 'RadC':
                scifile_metadata['top']['sector_name'] = 'CONUS'
            scifile_metadata['top']['sector_definition'] = None
        adname = scifile_metadata['top']['sector_name']

        # If an empty list of channels was requested, just stop here and output the metadata
        if chans == []:
            return

        # Create list of all possible channels for the case where no channels were requested
        all_chans_list = []
        for chl in self.all_chans.values():
            all_chans_list += chl

        # If specific channels were requested, check them against the input data
        # If specific channels were requested, but no files exist for one of the channels, then error
        if chans:
            for chan in chans:
                if chan not in all_chans_list:
                    raise ValueError('Requested channel {0} not recognized.'.format(chan))
                if chan[0:3] not in file_info.keys():
                    continue
                    # raise ValueError('Requested channel {0} not found in input data.'.format(chan))

        # If no specific channels were requested, get everything
        if not chans:
            chans = all_chans_list

        # Creates dict whose keys are band numbers in the form B## and whose values are lists
        # containing the data types(s) requested for the band (e.g. Rad, Ref, BT).
        chan_info = {}
        for ch in chans:
            chn = ch[0:3]
            typ = ch[3:]
            if chn not in chan_info:
                chan_info[chn] = []
            chan_info[chn].append(typ)

        # Gather geolocation data
        # Assume datetime the same for all resolutions.  Not true, but close enough.
        # This save us from having very slightly different solar angles for each channel.
        # Loop over resolutions and get metadata as needed
        if self_register:
            log.info('')
            log.interactive('Getting geolocation information for resolution {} for {}.'.format(
                self_register, adname))
            gvars[adname] = get_geolocation(sdt, res_md[self_register], sector_definition)
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
                try:
                    gvars[res] = get_geolocation(sdt, res_md[res], sector_definition)
                except ValueError, resp:
                    log.error('{} GEOLOCATION FAILED FOR {} resolution {}. Skipping.'.format(
                        resp, adname, res))
                # Not sure what this does, but it fails if we only pass one resolution worth of data...
                # MLS I think this may be necessary to avoid catastrophic failure if geolocation has not been
                # autogenerated.  I'll see.
                # if not gvars[res]:
                #     log.error('GEOLOCATION FAILED for '+adname+' resolution '+res+' DONT_AUTOGEN_GEOLOCATION is: '\
                #               +str(DONT_AUTOGEN_GEOLOCATION))
                #     gvars[res] = {}

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
                log.interactive("We don't have geolocation information for {} for {} skipping {}.".format(
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
            if self_register:
                data = self.get_data(chan_md, gvars[adname], rad, ref, bt)
            else:
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
                if adname not in gvars and res in gvars and gvars[res]:
                    gvars[adname] = gvars[res]
                try:
                    gvars.pop(res)
                except KeyError:
                    pass

        if self_register:
            # Determine which resolution has geolocation
            log.info('Registering to {}'.format(self_register))
            if self_register == 'HIGH':
                datavars[adname] = datavars.pop('HIGH')
                for varname, var in datavars['LOW'].items():
                    datavars[adname][varname] = zoom(var, 4, order=0)
                datavars.pop('LOW')
                for varname, var in datavars['MED'].items():
                    datavars[adname][varname] = zoom(var, 2, order=0)
                datavars.pop('MED')

            elif self_register == 'MED':
                datavars[adname] = datavars.pop('MED')
                for varname, var in datavars['LOW'].items():
                    datavars[adname][varname] = zoom(var, 2, order=0)
                datavars.pop('LOW')
                for varname, var in datavars['HIGH'].items():
                    datavars[adname][varname] = var[::2, ::2]
                datavars.pop('HIGH')

            elif self_register == 'LOW':
                datavars[adname] = datavars.pop('LOW')
                for varname, var in datavars['MED'].items():
                    datavars[adname][varname] = var[::2, ::2]
                datavars.pop('MED')
                for varname, var in datavars['HIGH'].items():
                    datavars[adname][varname] = var[::4, ::4]
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
        log.interactive('Done reading ABI data for ' + adname)
        log.info('')
        return

    @staticmethod
    def get_data(md, gvars, rad=False, ref=False, bt=False):
        '''
        Read data for a full channel's worth of files.
        '''
        # Coordinate arrays for reading
        if ('Lines' in gvars and 'Samples' in gvars):
            full_disk = False
            line_inds = gvars['Lines']
            sample_inds = gvars['Samples']
        else:
            full_disk = True

        # Open the data file for reading
        df = ncdf.Dataset(md['path'], 'r')

        band_num = md['var_info']['band_id']

        # Read radiance data for channel
        # For some reason, netcdf4 does not like it if you pass a bunch of indexes.
        # It is very slow and creates memory errors if there are too many.
        # Have to read ALL of the data, then subset.
        # Need to find a solution for this.
        if not full_disk:
            data = {'Rad': np.float64(df.variables['Rad'][...][line_inds, sample_inds])}
            qf = df.variables['DQF'][...][line_inds, sample_inds]
        else:
            data = {'Rad': np.float64(df.variables['Rad'][...])}
            qf = df.variables['DQF'][...]

        # If reflectance is requested
        # Note, weird memory manipulations to save memory when radiances are not requested
        if ref:
            if band_num not in range(1, 7):
                raise ValueError('Unable to calculate reflectances for band #{0}'.format(band_num))

            # Get the radiance data
            # Have to do this when using numexpr
            rad_data = data['Rad']  # NOQA

            # If we don't need radiances, then reuse the memory
            if not rad:
                data['Ref'] = data.pop('Rad')
            else:
                data['Ref'] = np.empty_like(rad_data)

            k0 = md['var_info']['kappa0']  # NOQA
            sun_zenith = gvars['SunZenith']  # NOQA
            zoom_info = np.array(rad_data.shape, dtype=np.float) / np.array(sun_zenith.shape, dtype=np.float)
            if zoom_info[0] == zoom_info[1] and int(zoom_info[0]) == zoom_info[0]:
                if zoom_info[0] > 1 and int(zoom_info[0]) == zoom_info[0]:
                    sun_zenith = zoom(sun_zenith, zoom_info[0])
                elif zoom_info[0] < 1 and int(zoom_info[0]**-1) == zoom_info[0]**-1:
                    sun_zenith = sun_zenith[::zoom_info[0]**-1, :: zoom_info[0]**-1]
                elif zoom_info[0] == 1:
                    pass
                else:
                    ValueError('Inappropriate zoom level calculated.')
            else:
                ValueError('Inappropriate zoom level calculated.')

            deg2rad = np.pi / 180.0  # NOQA
            ne.evaluate('k0 * rad_data / cos(deg2rad * sun_zenith)', out=data['Ref'])

        if bt:
            if band_num not in range(7, 17):
                raise ValueError('Unable to calculate brightness temperatures for band #{0}'.format(band_num))

            # Get teh radiance data
            # Have to do this when using numexpr
            rad_data = data['Rad']  # NOQA

            # If we don't need radiances, then reuse the memory
            if not rad:
                data['BT'] = data.pop('Rad')
            else:
                data['BT'] = np.empty_like(data['Rad'])

            fk1 = md['var_info']['planck_fk1']  # NOQA
            fk2 = md['var_info']['planck_fk2']  # NOQA
            bc1 = md['var_info']['planck_bc1']  # NOQA
            bc2 = md['var_info']['planck_bc2']  # NOQA

            data['BT'] = ne.evaluate('(fk2 / log(fk1 / rad_data + 1) - bc1) / bc2')

        for val in data.values():
            val[np.where(qf == -1)] = BADVALS['Off_Of_Disk']
            val[np.where(qf == 1)] = BADVALS['Conditional']
            # val[np.where(qf == 2)] = BADVALS['Out_Of_Valid_Range']
            val[np.where(qf == 3)] = BADVALS['No_Value']

        return data
