from __future__ import print_function

import os
import logging
import numpy as np

try:
    import numexpr as ne
except:
    pass

from hashlib import md5

from pyresample.geometry import SwathDefinition
from pyresample.kd_tree import get_neighbour_info

from geoips.utils.plugin_paths import paths as gpaths

debug = False
nproc = 1
ne.set_num_threads(nproc)

log = logging.getLogger(__name__)

DONT_AUTOGEN_GEOLOCATION = False
if os.getenv('DONT_AUTOGEN_GEOLOCATION'):
    DONT_AUTOGEN_GEOLOCATION = True

# 20181220 MLS: Updated satnav with Cervando's previous update to 
# geolocation generation in ABI and AHI readers.
# Initially satnav was set up to allow overriding the geolocation directory using an
# environment variable, we have since consolidated the geolocation to $SATOPS
# 20180910 CAB:
# Geolocation files are now no longer moved to localscratch and are now from 
# the SATOPS directory. Also the path is slightly different for dynamic sectors

GEOLOCDIR = os.path.join(gpaths['SATOPS'], 'longterm_files', 'geolocation')
#if os.getenv('GEOLOCDIR'):
#    GEOLOCDIR = os.getenv('GEOLOCDIR')

DYNAMIC_GEOLOCDIR = os.path.join(gpaths['SATOPS'], 'longterm_files', 'geolocation_dynamic')
#if os.getenv('DYNAMIC_GEOLOCDIR'):
#    DYNAMIC_GEOLOCDIR = os.getenv('DYNAMIC_GEOLOCDIR')

READ_GEOLOCDIRS = []
if os.getenv('READ_GEOLOCDIRS'):
    READ_GEOLOCDIRS = os.getenv('READ_GEOLOCDIRS').split(':')


class SatNavError(Exception):
    pass


class SatNavMetadataError(Exception):
    '''
    An error derived from the SatNavError exception that is raised
    when there is a problem with the input metadata.
    '''
    pass


class AutoGenError(SatNavError):
    pass


class SatNav(object):
    '''
    Produces or retrieves geolocation data from a file cache depending on
    if the file cache exists yet or not.  Available geolocation data include
    latitude, longitude, satellite azimuth, satellite zenith, solar azimuth,
    solar zenith, and the x and y indexes required for a specific domain.
    '''
    def __init__(self, sensor, scan_mode, lon0, num_lines, num_samples,
                 line_scale, sample_scale, line_offset, sample_offset,
                 start_datetime):
        log.debug('Initializing SatNav object.')

        # Container for generated datasets
        self._data = {}
        self._curr_sector = None
        self._curr_data = {}

        # "Protected" storage for metadata
        self._md = {'sensor': sensor,
                    'scan_mode': scan_mode,
                    'lon0': lon0,
                    'num_lines': num_lines,
                    'num_samples': num_samples,
                    'line_scale': line_scale,
                    'sample_scale': sample_scale,
                    'line_offset': line_offset,
                    'sample_offset': sample_offset,
                    'datetime': start_datetime}
        log.debug('Received: {}'.format(self._md))

        # Test input arguments
        # Everything except 'sensor' must be a number
        log.debug('Testing inputs')
        for arg, val in self._md.items():
            if arg in ['sensor', 'scan_mode', 'datetime']:
                continue
            try:
                val / 1
            except TypeError:
                raise SatNavMetadataError(
                    'Positional argument {} must be a number.  Got {}.'.format(arg, val))

        # Make sure subpoint is in range
        if lon0 < -180 or lon0 > 180:
            raise SatNavMetadataError(
                'Argument out of range: lon0 must be between -180 and 180. Got {}.'.format(lon0))

        # Check that these are whole numbers
        whole_numbers = ['num_lines', 'num_samples', 'line_offset', 'sample_offset']
        for arg in whole_numbers:
            if self._md[arg] % 1 != 0:
                raise SatNavMetadataError(
                    'Argument {} must be a whole number.  Got {}.'.format(arg, self._md[arg]))

        # # Check that these are positive
        # positive_numbers = ['line_scale', 'sample_scale']
        # positive_numbers.extend(whole_numbers)
        # for arg in positive_numbers:
        #     if self._md[arg] < 0:
        #         raise SatNavMetadataError(
        #             'Argument {} must be a positive number.  Got {}.'.format(arg, self._md[arg]))

        # Create the metadata hash (used in cache filenames)
        try:
            self._md_hash = hash(frozenset(self._md))
        # If this failed with a TypeError, determine which values were not
        # hashable and raise a more informative error
        except TypeError:
            unhashable = []
            for mdk, mdv in self._md.items():
                try:
                    hash(mdv)
                except TypeError:
                    unhashable.append(mdk)
            raise SatNavMetadataError(
                'Unhashable metadata encountered in {}'.format(', '.join(unhashable)))

        # Create all relevant cache filenames
        log.debug('Creating cache filenames.')
        self._cache_fnames_fd = {'GEOLL': self._get_cache_filename('GEOLL'),
                                 'GEOSAT': self._get_cache_filename('GEOSAT'),
                                 'GEOINDS': self._get_cache_filename('GEOINDS')}
        log.debug('{}'.format(self._cache_fnames_fd))

    def get_geolocation(self, sector=None):
        '''
        Return a dictionary whose keys are:
            Latitude, Longitude, SatZenith, SatAzimuth, SunZenith, SunAzimuth
        And whose values are numpy arrays containing the associated angle data.
        Data off the disk is set to -999.1.

        If a sector is not provided, the resulting arrays will be for the full
        input dataset.  If a sector is provided, the resulting arrays will
        be registered to the sector via nearest neighbor interpolation.
        '''
        data = {}
        if sector is None:
            log.info('Gathering geolocation for full dataset.')
            data['Latitude'] = self._lats_fd
            data['Longitude'] = self._lons_fd
            data['SatZenith'] = self._sat_zen_fd
            data['SatAzimuth'] = self._sat_azm_fd
            data['SunZenith'], data['SunAzimuth'] = self._calc_sun_angs()
        else:
            log.info('Gathering geolocation for {} sector.'.format(sector.name))
            data['Lines'], data['Samples'] = self.get_lines_samples(sector)
            data['Latitude'], data['Longitude'] = self.get_lats_lons(sector)
            data['SatZenith'], data['SatAzimuth'] = self.get_sat_angs(sector)
            data['SunZenith'], data['SunAzimuth'] = self.get_sun_angs(sector)
        return data

    def get_lats_lons(self, sector=None):
        '''
        Return two numpy arrays containing latitudes and longitudes, respectively.
        Locations off of the disk are set to -999.1.
        If no sector is provided, the resulting data will be for the full domain
        of the input data.  If a sector is provided, the resulting data will
        be registered to the sector via nearest neighbor interpolation.
        '''
        log.debug('Gathering latitudes and longitudes.')
        if sector is None:
            log.debug('No sector provided. Using latitudes and longitudes for full data domain.')
            return self._lats_fd, self._lons_fd

        # If this is the same sector as the previous sector,
        # then check for previous values and return them if they exist
        # If they don't exist, then recacluate them
        log.debug('Gathering latitudes and longitudes for {} sector.'.format(sector.name))
        if sector == self._curr_sector:
            if 'lats' in self._curr_data and 'lons' in self._curr_data:
                log.debug('Sector is the same as the last request.  Returning the same data.')
                return self._curr_data['lats'], self._curr_data['lons']
        # If this is a different sector, reset
        elif self._curr_sector is not None:
            self._curr_sector = None
            self._curr_data = {}

        cache = self._get_cache_filename('GEOLL', sector)
        log.debug('GEOLL cache filename: {}'.format(cache))
        if not os.path.isfile(cache):
            log.debug('Getting lines and samples for {} sector.'.format(sector.name))
            lines, samples = self.get_lines_samples(sector)
            bad_mask = lines > -999
            lats = np.full(lines.shape, -999.1, dtype=np.float64)
            lons = np.full(lines.shape, -999.1, dtype=np.float64)
            log.debug('Subsetting from full latitude and longitude arrays.')
            lats[bad_mask] = self._lats_fd[lines[bad_mask], samples[bad_mask]]
            lons[bad_mask] = self._lons_fd[lines[bad_mask], samples[bad_mask]]

            log.debug('Writing latitudes and longitudes to cache file: {}'.format(cache))
            with open(cache, 'w') as cache_file:
                lats.tofile(cache_file)
                lons.tofile(cache_file)

        # Read from the cache
        log.debug('Reading latitudes and longitudes from cache file: {}'.format(cache))
        ad = sector.area_definition
        shape = ad.shape
        offset = 8 * shape[0] * shape[1]
        lats = np.memmap(cache, mode='r', dtype=np.float64, offset=0, shape=shape)
        lons = np.memmap(cache, mode='r', dtype=np.float64, offset=offset, shape=shape)

        self._curr_sector = sector
        self._curr_data['lats'] = lats
        self._curr_data['lons'] = lons
        log.debug('Latitudes:  min={} max={}'.format(lats.min(), lats.max()))
        log.debug('Longitudes: min={} max={}'.format(lons.min(), lons.max()))

        return lats, lons

    def get_sat_angs(self, sector=None):
        '''
        Return two numpy arrays containing latitudes and longitudes, respectively.
        Locations off of the disk are set to -999.1.
        If no sector is provided, the resulting data will be for the full domain
        of the input data.  If a sector is provided, the resulting data will
        be registered to the sector via nearest neighbor interpolation.
        '''
        log.debug('Gathering satellite zenith and azimuth angles.')
        if sector is None:
            log.debug('No sector provided. Using satellite angles for full data domain.')
            return self._sat_zen_fd, self._sat_azm_fd

        # If this is the same sector as the previous sector,
        # then check for previous values and return them if they exist
        # If they don't exist, then recacluate them
        log.debug('Gathering satellite angles for {} sector.'.format(sector.name))
        if sector == self._curr_sector:
            if 'sat_zen' in self._curr_data and 'sat_azm' in self._curr_data:
                log.debug('Sector is the same as the last request.  Returning the same data.')
                return self._curr_data['sat_zen'], self._curr_data['sat_azm']
        # If this is a different sector, reset
        elif self._curr_sector is not None:
            self._curr_sector = None
            self._curr_data = {}

        cache = self._get_cache_filename('GEOSAT', sector)
        log.debug('GEOSAT cache filename: {}'.format(cache))
        if not os.path.isfile(cache):
            log.debug('No cache file. Getting lines and samples for {} sector.'.format(sector.name))
            lines, samples = self.get_lines_samples(sector)
            bad_mask = lines > -999
            zen = np.full(lines.shape, -999.1, dtype=np.float64)
            azm = np.full(lines.shape, -999.1, dtype=np.float64)
            log.debug('Subsetting from full satellite angle arrays.')
            zen[bad_mask] = self._sat_zen_fd[lines[bad_mask], samples[bad_mask]]
            azm[bad_mask] = self._sat_azm_fd[lines[bad_mask], samples[bad_mask]]

            log.debug('Writing satellite angles to cache file: {}'.format(cache))
            with open(cache, 'w') as cache_file:
                zen.tofile(cache_file)
                azm.tofile(cache_file)

        # Read from the cache
        log.debug('Reading satellite angles from cache file: {}'.format(cache))
        ad = sector.area_definition
        shape = ad.shape
        offset = 8 * shape[0] * shape[1]
        zen = np.memmap(cache, mode='r', dtype=np.float64, offset=0, shape=shape)
        azm = np.memmap(cache, mode='r', dtype=np.float64, offset=offset, shape=shape)

        self._curr_sector = sector
        self._curr_data['sat_zen'] = zen
        self._curr_data['sat_azm'] = azm
        log.debug('SatZenith:  min={} max={}'.format(zen.min(), zen.max()))
        log.debug('SatAzimuth: min={} max={}'.format(azm.min(), azm.max()))

        return zen, azm

    def get_sun_angs(self, sector=None):
        '''
        Return two numpy arrays containing solar zenith and azimuth angles,
        respectively.  Locations off of the disk are set to -999.1.
        If no sector is provided, the resulting data will be for the full domain
        of the input data.  If a sector is provided, the resulting data will
        be registered to the sector via nearest neighbor interpolation.
        '''
        log.debug('Gathering solar zenith and azimuth angles.')
        if sector is None:
            log.debug('No sector provided. Using solar angles for full data domain.')
            return self._sun_zen_fd, self._sat_zen_fd

        # If this is the same sector as the previous sector,
        # then check for previous values and return them if they exist
        # If they don't exist, then recacluate them
        log.debug('Gathering solar angles for {} sector.'.format(sector.name))
        if sector == self._curr_sector:
            if 'sun_zen' in self._curr_data and 'sun_azm' in self._curr_data:
                log.debug('Sector is the same as the last request.  Returning the same data.')
                return self._curr_data['sun_zen'], self._curr_data['sun_azm']
        # If this is a different sector, reset
        elif self._curr_sector is not None:
            self._curr_sector = None
            self._curr_data = {}

        log.debug('Calculating solar angles.')
        zen, azm = self._calc_sun_angs(sector)
        self._curr_sector = sector
        self._curr_data['sun_zen'] = zen
        self._curr_data['sun_azm'] = azm
        log.debug('SunZenith:  min={} max={}'.format(zen.min(), zen.max()))
        log.debug('SunAzimuth: min={} max={}'.format(azm.min(), azm.max()))

        return zen, azm

    def get_lines_samples(self, sector):
        '''
        Attempt to gather arrays of required X and Y indexes in the
        original data space for the input sector.  First attempt to find a
        cache file.  It it doesn't exist, calculate the indexes and create
        the cache.
        '''
        log.debug('Gathering line and sample indexes for {} sector.'.format(sector))
        # If the most recently used sector is the current sector
        # then return the stored lines and samples
        # Otherwise, gather new lines and samples
        if self._curr_sector == sector:
            return self._curr_lines, self._curr_samples

        cache = self._get_cache_filename('GEOINDS', sector)
        log.debug('GEOINDS cache filename: {}'.format(cache))

        # If the file doesn't exist, create it
        if not os.path.isfile(cache):
            log.debug('No cache file.  Calculating line and sample indexes.')
            lines, samples = self._calc_lines_samples(sector)
            log.debug('Writing line and sample indexes to cache file: {}'.format(cache))
            with open(cache, 'w') as cache_file:
                lines.tofile(cache_file)
                samples.tofile(cache_file)

        # Read from the cache
        log.debug('Reading line and sample indexes from cache file: {}'.format(cache))
        shape = sector.area_definition.shape
        offset = 8 * shape[0] * shape[1]
        lines = np.memmap(cache, mode='r', dtype=np.int64, offset=0, shape=shape)
        samples = np.memmap(cache, mode='r', dtype=np.int64, offset=offset, shape=shape)

        # Store the lines and samples for the current sector
        # for use in other routines
        # Overwrites each time a new sector is used
        self._curr_sector = sector
        self._curr_lines = lines
        self._curr_samples = samples
        log.debug('lines:   min={} max={}'.format(lines.min(), lines.max()))
        log.debug('samples: min={} max={}'.format(samples.min(), samples.max()))

        return lines, samples

    '''
    Properties to expose metadata properties.
    I do this kind of thing to limit an inexperienced user's ability to break
    instances of the class after creation by changing the input metadata.
    Python's "We're all adults here" ideal can only be trusted so far.
    '''
    @property
    def sensor(self):
        return self._md['sensor']

    @property
    def scan_mode(self):
        return self._md['scan_mode']

    @property
    def lon0(self):
        return self._md['lon0']

    @property
    def num_lines(self):
        return self._md['num_lines']

    @property
    def num_samples(self):
        return self._md['num_samples']

    @property
    def line_scale(self):
        return self._md['line_scale']

    @property
    def sample_scale(self):
        return self._md['sample_scale']

    @property
    def line_offset(self):
        return self._md['line_offset']

    @property
    def sample_offset(self):
        return self._md['sample_offset']

    def _get_cache_filename(self, prefix, sector=None):
        '''
        Produces a filename that will be used to cache pre-computed
        geolocation values for easy retrieval.
        '''
        cache = GEOLOCDIR
        if sector and sector.isdynamic:
            cache = DYNAMIC_GEOLOCDIR
        cache = os.path.join(cache, self.sensor)
        if not os.path.isdir(cache):
            os.makedirs(cache)

        fname = '{}_{}_{}_{}x{}'.format(self.sensor, prefix, self.scan_mode,
                                        self.num_lines, self.num_samples)
        md_dict = self._md.copy()
        if sector is not None:
            ad = sector.area_definition
            sect_num_lines = ad.shape[0]
            sect_num_samples = ad.shape[1]
            sect_clat = sector.area_info.center_lat_float
            sect_clon = sector.area_info.center_lon_float
            fname = '{}_{}_{}x{}_{}x{}'.format(
                fname, sector.name, sect_num_lines, sect_num_samples, sect_clat, sect_clon)
            md_dict.update(ad.proj_dict)
        md_dict.pop('datetime')
        log.info(md_dict.__str__())
        md_hash = md5(md_dict.__str__()).hexdigest()
        log.info(md_hash)
        fname = '{}_{}.DAT'.format(fname, md_hash)

        return os.path.join(cache, fname)

    def _calc_x_y(self):
        '''
        Generate intermediate cartesian coordinates.
        These are floating point arrays whose origin is located in the center
        of the data.  These are an intermediate step between image coordinates
        and latitudes/longitudes and are not useful in other applicatons.
        '''
        deg2rad = np.pi / 180.0
        x, y = np.meshgrid(np.arange(0, self.num_samples, 1), np.arange(0, self.num_lines, 1))
        x = np.fliplr(x)
        y = np.fliplr(y)
        self._data['x'] = deg2rad * (x - self.sample_offset) / (2**-16 * self.sample_scale)
        self._data['y'] = deg2rad * (y - self.line_offset) / (2**-16 * self.line_scale)

    def _calc_lats_lons(self):
        '''
        Generate full-disk latitudes and longitudes.
        '''
        # Constants
        pi = np.pi
        rad2deg = 180.0 / pi
        deg2rad = pi / 180.0
        Rs = 42164  # Satellite altitude (km)
        Re = 6378.1690  # Earth equatorial radius (km)
        Rp = 6356.5838  # Earth polar radius (km)
        r3 = Re**2 / Rp**2
        sd_coeff = 1737122264  # If there is a problem for MSG use 1737121856
        lon0 = self.lon0

        cos_x = np.cos(self._x_fd)
        sin_x = np.sin(self._x_fd)
        cos_y = np.cos(self._y_fd)
        sin_y = np.sin(self._y_fd)

        sd = ne.evaluate('(Rs * cos_x * cos_y)**2 - (cos_y**2 + r3 * sin_y**2) * sd_coeff')
        bad_mask = sd < 0.0
        sd[bad_mask] = 0.0
        sd **= 0.5

        # Doing inplace operations when variables are no longer needed

        # sd no longer needed
        sn = sd
        ne.evaluate('(Rs * cos_x * cos_y - sd) / (cos_y**2 + r3 * sin_y**2)', out=sn)

        # cos_x no longer needed
        s1 = cos_x
        ne.evaluate('Rs - (sn * cos_x * cos_y)', out=s1)

        # Nothing unneed, no inplace
        s2 = ne.evaluate('sn * sin_x * cos_y')

        # sin_y no longer needed
        s3 = cos_y
        ne.evaluate('-sn * sin_y', out=s3)

        # sn no longer needed
        sxy = sn
        ne.evaluate('sqrt(s1**2 + s2**2)', out=sxy)

        # s3 no longer needed
        lats = s3
        ne.evaluate('rad2deg * arctan(r3 * s3 / sxy)', out=lats)

        # s1 no longer needed
        lons = s1
        ne.evaluate('rad2deg * arctan(s2 / s1) + lon0', out=lons)
        lons[lons > 180.0] -= 360

        # Set bad values
        lats[bad_mask] = -999.1
        lons[bad_mask] = -999.1

        return lats, lons

    def _gather_lats_lons(self):
        '''
        Attempt to read full disk latitudes and longitues from cache.
        If cache doesn't exist, calculate latitudes and longitudes
        and store in the cache.
        '''
        cache = self._cache_fnames_fd['GEOLL']

        # If the cache doesn't exist, create it
        if not os.path.isfile(cache):
            lats, lons = self._calc_lats_lons()
            with open(cache, 'w') as cache_file:
                lats.tofile(cache_file)
                lons.tofile(cache_file)

        # Read from the cache
        shape = (self.num_lines, self.num_samples)
        offset = 8 * self.num_lines * self.num_samples
        self._data['lats'] = np.memmap(cache, mode='r', dtype=np.float64, offset=0, shape=shape)
        self._data['lons'] = np.memmap(cache, mode='r', dtype=np.float64, offset=offset, shape=shape)
        self._data['bad_mask'] = self._data['lats'] == -999.1

    def _calc_sat_angs(self):
        '''
        Generate full-disk latitudes and longitudes.
        '''
        # Constants
        sub_lat = 0.0  # Always 0.0 for geostationary
        sub_lon = self.lon0
        rad2deg = 180.0 / np.pi
        deg2rad = np.pi / 180.0
        Rs = 42164  # Satellite altitude (km)

        lats = self._lats_fd
        lons = self._lons_fd
        bad_mask = lats == -999.1

        # Convert lats/lons to radians from sub point
        beta = ne.evaluate('arccos(cos(deg2rad * (lats - sub_lat)) * '
                           + 'cos(deg2rad * (lons - sub_lon)))')

        # Calculate satellite zenith angle
        zen = ne.evaluate('Rs * sin(beta) / sqrt(1.808e9 - 5.3725e8 * cos(beta))')
        ne.evaluate('rad2deg * arcsin(where(zen < -1.0, -1.0, where(zen > 1.0, 1.0, zen)))', out=zen)

        # Calculate sat azimuth
        azm = ne.evaluate('sin(deg2rad * (lons - sub_lon)) / sin(beta)')
        ne.evaluate('rad2deg * arcsin(where(azm < -1.0, -1.0, where(azm > 1.0, 1.0, azm)))', out=azm)
        ne.evaluate('where(lats < sub_lat, 180.0 - azm, azm)', out=azm)
        ne.evaluate('where(azm < 0.0, 360.0 + azm, azm)', out=azm)

        # Set bad values
        zen[bad_mask] = -999.1
        azm[bad_mask] = -999.1

        return zen, azm

    def _gather_sat_angs(self):
        '''
        Attempt to read full disk satellite angles from cache.
        If cache doesn't exist, calculate latitudes and longitudes
        and store in the cache.
        '''
        cache = self._cache_fnames_fd['GEOSAT']

        # If the cache doesn't exist, create it
        if not os.path.isfile(cache):
            zen, azm = self._calc_sat_angs()
            with open(cache, 'w') as cache_file:
                zen.tofile(cache_file)
                azm.tofile(cache_file)

        # Read from the cache
        shape = (self.num_lines, self.num_samples)
        offset = 8 * self.num_lines * self.num_samples
        self._data['sat_zen'] = np.memmap(cache, mode='r', dtype=np.float64, offset=0, shape=shape)
        self._data['sat_azm'] = np.memmap(cache, mode='r', dtype=np.float64, offset=offset, shape=shape)

    def _calc_sun_angs(self, sector=None):
        '''
        Calculate the solar zenith and azimuth angles for the current
        datetime.  Optionally, latitude and longitude arrays may be
        provided.  If they are provided, angles will be calculated only
        for those locations.  Otherwise, angles will be calculated for
        the full disk.
        '''
        pi = np.pi
        deg2rad = pi / 180.0
        rad2deg = 180.0 / pi

        if sector is None:
            lats = self._lats_fd
            lons = self._lons_fd
        else:
            lats, lons = self.get_lats_lons(sector)

        # Calculate any non-data dependent quantities
        dt = self._md['datetime']
        jday = float(self._md['datetime'].strftime('%j'))
        a1 = deg2rad * (1.00554 * jday - 6.28306)
        a2 = deg2rad * (1.93946 * jday - 23.35089)
        et = -7.67825 * np.sin(a1) - 10.09176 * np.sin(a2)

        # Solar declination (radians)
        delta = deg2rad * 23.4856 * np.sin(np.deg2rad(0.9683 * jday - 78.00878))

        # Solar time
        solar_time = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        # Hour angle
        h_ang = deg2rad * ((solar_time + lons / 15.0 + et / 60.0 - 12.0) * 15.0)

        # Precalculating since needed multiple times later
        sin_lat = np.sin(deg2rad * lats)
        cos_lat = np.cos(deg2rad * lats)

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

        sun_zen[lats == -999.1] = -999.1
        sun_azm[lats == -999.1] = -999.1

        return sun_zen, sun_azm

    def _gather_sun_angs(self):
        '''
        This method just makes sun_angs work the same as lats_lons and sat_angs.
        Mainly here to avoid confusion.

        Unlike the other '_gather' methods, this does not check a cache on disk
        since the solar angles must be recalculated for each image.
        '''
        if 'sun_zen' not in self._data or 'sun_azm' not in self._data:
            self._data['sun_zen'], self._data['sun_azm'] = self._calc_sun_angs()

    def _calc_lines_samples(self, sector):
        # Allocate the full disk area definition
        fldk_ad = SwathDefinition(np.ma.masked_less_equal(self._lons_fd, -999.0),
                                  np.ma.masked_less_equal(self._lats_fd, -999.0))
        ad = sector.area_definition

        # Determine the nominal spatial resolution at nadir
        shape = self._lons_fd.shape
        # Resolution in meters
        latres = np.abs(self._lats_fd[shape[0] / 2, shape[1] / 2]
                        - self._lats_fd[shape[0] / 2 + 1, shape[1] / 2]) * 111.1 * 1000
        lonres = np.abs(self._lons_fd[shape[0] / 2, shape[1] / 2]
                        - self._lons_fd[shape[0] / 2, shape[1] / 2 + 1]) * 111.1 * 1000
        # Use larger of the two values times 10 as ROI for interpolation
        # Would be nice to use something more dynamic to save CPU time here
        # Kind of stuck as long as we use pyresample
        roi = 10 * max(latres, lonres)

        # Do the first step of the NN interpolation
        valid_input_index, valid_output_index, index_array, distance_array = \
            get_neighbour_info(fldk_ad, ad, radius_of_influence=roi, neighbours=1, nprocs=nproc)
        if not valid_input_index.any():
            raise SatNavError('{} sector does not intersect data.'.format(sector.name))

        # Determine which lines and samples intersect our domain.
        good_lines, good_samples = np.where(valid_input_index.reshape(shape))
        # When get_neighbour_info does not find a good value for a specific location it
        # fills index_array with the maximum index + 1.  So, just throw away all of the
        # out of range indexes.
        index_mask = (index_array == len(good_lines))
        lines = np.empty(ad.size, dtype=np.int64)
        lines[index_mask] = -999.1
        lines[~index_mask] = good_lines[index_array[~index_mask]]
        samples = np.empty(ad.size, dtype=np.int64)
        samples[index_mask] = -999.1
        samples[~index_mask] = good_samples[index_array[~index_mask]]

        return lines, samples

    '''
    The following properties return arrays for the full disk.
    These should not be needed by the user.
    Users should instead use the non-understored properties.
    '''
    @property
    def _x_fd(self):
        if 'x' not in self._data:
            self._calc_x_y()
        return self._data['x']

    @property
    def _y_fd(self):
        if 'y' not in self._data:
            self._calc_x_y()
        return self._data['y']

    @property
    def _bad_mask_fd(self):
        if 'bad_mask' not in self._data:
            self._gather_lats_lons()
        return self._data['bad_mask']

    @property
    def _lats_fd(self):
        if 'lats' not in self._data:
            self._gather_lats_lons()
        return self._data['lats']

    @property
    def _lons_fd(self):
        if 'lons' not in self._data:
            self._gather_lats_lons()
        return self._data['lons']

    @property
    def _sat_zen_fd(self):
        if 'sat_zen' not in self._data:
            self._gather_sat_angs()
        return self._data['sat_zen']

    @property
    def _sat_azm_fd(self):
        if 'sat_zen' not in self._data:
            self._gather_sat_angs()
        return self._data['sat_azm']

    @property
    def _sun_zen_fd(self):
        if 'sun_zen' not in self._data:
            self._gather_sun_angs()
        return self._data['sun_zen']

    @property
    def _sun_azm_fd(self):
        if 'sun_zen' not in self._data:
            self._gather_sun_angs()
        return self._data['sun_azm']

    @property
    def _xinds(self):
        pass

    @property
    def _yinds(self):
        pass
