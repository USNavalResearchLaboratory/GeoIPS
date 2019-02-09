#!/bin/env python

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

# 20150630  Mindy  Added filename information to AMSUA/AMSUB/AMSR2/ASCAT
#                   GMI/GPROF/HIMAWARI/MTSATGS/FNMOCBFTGS

# Python Standard Libraries
import os
import logging
import socket


# Installed Libraries
from IPython import embed as shell
# from IPython.core.debugger import Tracer


# GeoIPS Libraries
from .log_setup import interactive_log_setup
from .plugin_paths import paths as gpaths


log = interactive_log_setup(logging.getLogger(__name__))


class SatInfoError(Exception):
    '''
    Exception raised by SatInfo classes when invalid options requested
    '''
    def __init__(self, msg):
        self.value = msg

    def __str__(self):
        return self.value


class SatInfo(object):
    def __init__(self, sensor=None, satellite=None):
        # Pulled the attribute sets out of __init__ and put in separate
        # method
        self._set_SatInfo_atts(sensor=sensor)
        # The super in SatSensorInfo is only calling SatInfo __init__
        # Not sure how to fix this, but for now, if we call _set_SensorInfo_atts
        # from SatInfo.__init__, we are covered (all SensorInfo methods are
        # reflected in the SatSensorInfo class, the __init__ just isn't called)
        try:
            self._set_SensorInfo_atts(satellite=satellite)
        except AttributeError:
            pass
    
    def _set_SatInfo_atts(self, sensor=None, **kwargs):
        # Set default attributes here, instead of directly
        # in __init__, so SatInfo's attributes can be set
        # from SensorInfo and vice versa.
        # Probably is a better way to handle this, but this
        # works for now
        self.satname = self._get_satname()
        self.sensornames = None
        self.orbital_period = None
        self.testsatattr = 'hi sat!'
        self.geostationary = None
        self.satellite_dead = False
        self._set_satinfo()
        self._select_sensor(sensor)
        # This is used in scifile/containers.py register. Has to match biggest possible
        # pixel size (at edge of scan)
        self.interpolation_radius_of_influence = 100
        # If these values were not set in _set_satinfo, set them
        # to None here.  tle_name is the name used in
        # celestrak TLE files, tscan_name is name used in tscan
        # tscan tle files
        if not hasattr(self, 'celestrak_tle_name'):
            self.celestrak_tle_name = None
        if not hasattr(self, 'old_celestrak_tle_names'):
            self.old_celestrak_tle_names = []
        if not hasattr(self, 'tscan_tle_name'):
            self.tscan_tle_name = None
        # NOTE orig_file_satname is actually used in utils.path.datafilename to 
        # determine if current filename matches desired satellite.
        # THIS MUST MATCH satname FOUND IN FILENAME EXACTLY
        if not hasattr(self, 'orig_file_satname'):
            self.orig_file_satname = None

    def _set_satinfo(self):
        pass

#    @classmethod
    def _get_satname(self):
        for sat in SatInfo_classes.keys():
            if issubclass(self.__class__, SatInfo_classes[sat]):
                return sat
        return None

    def _select_sensor(self, sensor=None):
        usesensors = []
        if sensor:
            if sensor in self.sensornames:
                usesensors.append(sensor)
            else:
                err_msg = 'Invalid sensor {0} requested for satellite {1}.  Valid sensors are: {2}'.format(
                    sensor, self.satname, ' '.join(self.sensornames))
                raise SatInfoError(err_msg)
        else:
            return
        self.sensornames = usesensors
        return


class AQUASatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['modis', 'amsre']
        self.orbital_period = 98 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'AQUA'
        self.tscan_tle_name = 'aqua-1'
        self.geostationary = False


class CORIOLISSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['windsat']
        self.orbital_period = 100 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'CORIOLIS'
        self.tscan_tle_name = 'coriolis'
        self.geostationary = False


class F08SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['ssmis', 'ssmi', 'ols']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'F-08'
        self.tscan_tle_name = 'f-08'
        self.geostationary = False
        self.satellite_dead = True


class F10SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['ssmis', 'ssmi', 'ols']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'F-10'
        self.tscan_tle_name = 'f-10'
        self.geostationary = False
        self.satellite_dead = True


class F11SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['ssmis', 'ssmi', 'ols']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'F-11'
        self.tscan_tle_name = 'f-11'
        self.geostationary = False
        self.satellite_dead = True


class F13SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['ssmis', 'ssmi', 'ols']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'F-13'
        self.tscan_tle_name = 'f-13'
        self.geostationary = False
        self.satellite_dead = True


class F14SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['ssmis', 'ssmi', 'ols']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'F-13'
        self.tscan_tle_name = 'f-13'
        self.geostationary = False
        self.satellite_dead = True


class F15SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['ssmis', 'ssmi', 'ols']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'F-15'
        self.tscan_tle_name = 'f-15'
        self.geostationary = False


class F16SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['ssmis', 'ssmi', 'ols']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'F-16'
        self.tscan_tle_name = 'f-16'
        self.geostationary = False


class F17SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['ssmis', 'ssmi', 'ols']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'F-17'
        self.tscan_tle_name = 'f-17'
        self.geostationary = False


class F18SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['ssmis', 'ssmi', 'ols']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'F-18'
        self.tscan_tle_name = 'f-18'
        self.geostationary = False


class F19SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['ssmis', 'ssmi', 'ols']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'F-19'
        self.tscan_tle_name = 'f-19'
        self.geostationary = False


class G14SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['gvar']
        #self.orbital_period = 98 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'GOES 14'
        self.tscan_tle_name = 'goes-14'
        self.geoips_satname = 'g14'
        self.geostationary = True


class GCOMSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['amsr2']
        self.orbital_period = 98 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'GCOM-W1 (SHIZUKU)'
        self.tscan_tle_name = 'gcom-w1'
        self.geostationary = False


class GOESESatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        # MLS 20160504 This might break legacy code, but it makes things difficult for having a
        # common sensorname.  Possibly need to make a "default" sensorname, and
        # allow for alternatives ? For now, just force it to gvar
        #self.sensornames = ['gvar', 'goes', 'gvissr']
        self.sensornames = ['gvar']
        #self.orbital_period = 98 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'GOES 13'
        self.tscan_tle_name = 'goes-13'
        self.geoips_satname = 'goesE'
        # NOTE orig_file_satname is actually used in utils.path.datafilename to 
        # determine if current filename matches desired satellite.
        # THIS MUST MATCH satname FOUND IN FILENAME EXACTLY
        self.orig_file_satname = 'g13'
        self.geostationary = True

class SourceStitchedSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['sourcestitched']
        self.geoips_satname = 'sourcestitched'
        self.geostationary = True

class GOES17SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        # MLS 20160504 This might break legacy code, but it makes things difficult for having a
        # common sensorname.  Possibly need to make a "default" sensorname, and
        # allow for alternatives ? For now, just force it to gvar
        #self.sensornames = ['gvar', 'goes', 'gvissr']
        self.sensornames = ['abi', 'glm', 'clavrx-abi', 'ccbg-abi']
        #self.orbital_period = 98 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'GOES 17'
        self.geoips_satname = 'goes17'
        self.geostationary = True

class GOES16SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        # MLS 20160504 This might break legacy code, but it makes things difficult for having a
        # common sensorname.  Possibly need to make a "default" sensorname, and
        # allow for alternatives ? For now, just force it to gvar
        #self.sensornames = ['gvar', 'goes', 'gvissr']
        self.sensornames = ['abi', 'glm', 'clavrx-abi', 'ccbg-abi']
        #self.orbital_period = 98 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'GOES 16'
        self.geoips_satname = 'goes16'
        self.geostationary = True


class GOESWSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['gvar']
        #self.orbital_period = 98 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'GOES 15'
        self.tscan_tle_name = 'goes-15'
        self.geoips_satname = 'goesW'
        # NOTE orig_file_satname is actually used in utils.path.datafilename to 
        # determine if current filename matches desired satellite.
        # THIS MUST MATCH satname FOUND IN FILENAME EXACTLY
        self.orig_file_satname = 'g15'
        self.geostationary = True


class GPMSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['gmi', 'gprof']
        self.orbital_period = 95 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'GPM-CORE'
        self.tscan_tle_name = 'gpm'
        self.geostationary = False


class HIMAWARI8SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['ahi', 'clavrx-ahi', 'ccbg-ahi']
        #self.orbital_period = 92.5 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'HIMAWARI-8'
        self.old_celestrak_tle_names = ['HIMAWARI 8']
        self.tscan_tle_name = None
        self.geostationary = True


class ISSSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['rscat', 'rscat25', 'rscat_knmi_25']
        # 92.85 minutes
        self.orbital_period = 93 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'ISS (ZARYA)'
        self.tscan_tle_name = None
        self.geostationary = False

class M2ASatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['amsua', 'amsub']
        #self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = None
        self.tscan_tle_name = None
        self.geostationary = False


class ME8SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['seviri']
        #self.orbital_period = 92.5 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'METEOSAT-8 (MSG-1)'
        self.geoips_satname = 'meteoIO'
        self.tscan_tle_name = 'msg-1'
        # NOTE orig_file_satname is actually used in utils.path.datafilename to 
        # determine if current filename matches desired satellite.
        # THIS MUST MATCH satname FOUND IN FILENAME EXACTLY
        # ie, don't leave out the __
        self.orig_file_satname = 'MSG1__'
        self.geostationary = True


class ME9SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['seviri']
        #self.orbital_period = 92.5 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'METEOSAT-9 (MSG-2)'
        self.tscan_tle_name = 'msg-2'
        self.geoips_satname = 'meteoEU'
        # NOTE orig_file_satname is actually used in utils.path.datafilename to 
        # determine if current filename matches desired satellite.
        # THIS MUST MATCH satname FOUND IN FILENAME EXACTLY
        # ie, don't leave out the __
        self.orig_file_satname = 'MSG2__'
        self.geostationary = True


class ME10SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['seviri']
        #self.orbital_period = 92.5 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'METEOSAT-10 (MSG-3)'
        self.tscan_tle_name = 'msg-3'
        self.geostationary = True

class ME11SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['seviri']
        #self.orbital_period = 92.5 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'METEOSAT-11 (MSG-4)'
        self.tscan_tle_name = 'msg-4'
        self.geoips_satname = 'meteoEU'
        # NOTE orig_file_satname is actually used in utils.path.datafilename to 
        # determine if current filename matches desired satellite.
        # THIS MUST MATCH satname FOUND IN FILENAME EXACTLY
        # ie, don't leave out the __
        self.orig_file_satname = 'MSG4__'
        self.geostationary = True


class MEGHATROPIQUESSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['saphir']
        self.orbital_period = 101.93 * 60
        # period 101.93 min revs/day 14.13
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'MEGHA-TROPIQUES'
        self.tscan_tle_name = None
        self.geostationary = False


class METEO7SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['seviri']
        #self.orbital_period = 92.5 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'METEOSAT-7'
        self.tscan_tle_name = 'meteo-7'
        self.geostationary = True



class METOPASatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['ascat']
        self.orbital_period = 107.1 * 60.0
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'METOP-A'
        self.tscan_tle_name = 'metop-a'
        self.geostationary = False


class METOPBSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['ascat']
        self.orbital_period = 107.1 * 60.0
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'METOP-B'
        self.tscan_tle_name = 'metop-1'
        self.geostationary = False


class MODELSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['icap','navgem','coamps','naapsaot']
        #self.orbital_period = 107.1 * 60.0
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        #self.celestrak_tle_name = 'METOP-B'
        #self.tscan_tle_name = 'metop-1'
        #self.geostationary = False

class WindVectorsSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['winds']
        #self.orbital_period = 107.1 * 60.0
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        #self.celestrak_tle_name = 'METOP-B'
        #self.tscan_tle_name = 'metop-1'
        #self.geostationary = False


class MT1SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['jami', 'svissr']
        #self.orbital_period = 92.5 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'HIMAWARI-6 (MTSAT-1)'
        self.tscan_tle_name = None
        self.geostationary = False


class MT2SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['jami', 'svissr']
        #self.orbital_period = 92.5 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'HIMAWARI-7 (MTSAT-2)'
        self.tscan_tle_name = None
        self.geostationary = False


class MULTISatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['tpw_cira', 'tpw_mimic','merged']
        #self.orbital_period = 98 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        #self.celestrak_tle_name = 'GOES 13'
        #self.tscan_tle_name = 'goes-13'
        self.geostationary = False


class N15SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['amsua', 'amsub']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'NOAA 15'
        self.tscan_tle_name = 'noaa-15'
        self.geostationary = False


class N16SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['amsua', 'amsub']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'NOAA 16'
        self.tscan_tle_name = 'noaa-16'
        self.geostationary = False


class N18SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['amsua', 'amsub']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'NOAA 18'
        self.tscan_tle_name = 'noaa-18'
        self.geostationary = False


class N19SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['amsua', 'amsub']
        self.orbital_period = 102 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'NOAA 19'
        self.tscan_tle_name = 'noaa-19'
        self.geostationary = False


class NAVGEMSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['navgemforecast']
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)


class NPPSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['viirs', 'atms', 'cris']
        self.orbital_period = 101 * 60
        # tle names for celestrak and tscan, default to satname
        # if not defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'NPP'
        self.tscan_tle_name = 'npp'
        self.geostationary = False

class N20SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['viirs', 'atms', 'cris']
        self.orbital_period = 101 * 60
        # tle names for celestrak and tscan, default to satname
        # if not defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'NOAA 20'
        self.tscan_tle_name = 'noaa-20'
        self.geostationary = False

class NRLJCSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['mint']
        self.celestrak_tle_name = None
        self.tscan_tle_name = None
        self.geostationary = False


class OCEANSATSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['oscat']
        #self.orbital_period = 92.5 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = None
        self.tscan_tle_name = None
        self.geostationary = False


class PROTEUSSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['smos']
        #self.orbital_period = 92.5 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        #self.celestrak_tle_name = 'TRMM'
        #self.tscan_tle_name = 'trmm'
        self.geostationary = False
        self.satellite_dead = True


class SCATSAT1SatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['oscat']
        self.orbital_period = 100 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = None
        self.tscan_tle_name = None
        self.geostationary = False
        self.mins_per_file = 50

class SMAPSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['smap-spd']
        # self.orbital_period = 
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        self.celestrak_tle_name = 'SMAP'
        self.tscan_tle_name = None
        self.geostationary = False

class TERRASatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['modis']
        self.orbital_period = 98 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'TERRA'
        self.tscan_tle_name = 'terra-1'
        self.geostationary = False


class TRMMSatInfo(SatInfo):
    def _set_satinfo(self, sensor=None):
        self.sensornames = ['tmi']
        self.orbital_period = 92.5 * 60
        # tle names for celestrak and tscan, default to satname
        # if not, defined in _set_satinfo
        # None if not available (no ISS from tscan, no TLEs for GEO)
        self.celestrak_tle_name = 'TRMM'
        self.tscan_tle_name = 'trmm'
        self.geostationary = False
        self.satellite_dead = True


class SatSensorInfo(object):
    '''This replaces the pass_prediction.satellite_info method get_sensor_info
    call with satellite, sensor, and it returns the appropriate <Sat><Sensor>Info
    object.'''
    def __init__(self, satellite=None, sensor=None):
        #print 'In __init__ for SatSensorInfo'
        self._set_SensorInfo_atts(satellite=satellite)
        self._set_SatInfo_atts(sensor=sensor)
    def __new__(cls, satellite=None, sensor=None):
        '''
        Provide an easy interface for creating an object
        containing information from both the passed satellite
        and sensor.

        When called with no arguments, creates an empty object
        with some default attributes set (filename format, etc)

        When called with satellite and sensor, sets appropriate
        attributes from SensorInfo subclass and SatInfo subclass,
        and creates new class named <sensor><sat>Info'''
        #print 'In __new__ for SatSensorInfo'
        newclassname = ''
        # If satellite is passed as argument, create specific SatInfo class.
        if satellite:
            satinfo = SatInfo_classes[satellite](sensor=sensor)
            newclassname += satellite
        # otherwise create empty SatInfo
        else:
            satinfo = SatInfo(sensor=sensor)
            newclassname += 'GSat'

        if sensor:
            sensinfo = SensorInfo_classes[sensor](satellite=satellite)
            newclassname += sensor
        else:
            sensinfo = SensorInfo(satellite=satellite)
            newclassname += 'GSensor'

        #print "SatSensorInfo new"
        #print satinfo.__class__
        #print sensinfo.__class__

        #print 'newclassname: ' + newclassname
        # Create new class using SatInfo class and the calling class
        newcls = type(str('%sInfo' % newclassname), (satinfo.__class__, sensinfo.__class__), {})
        #print 'new class: ' + str(newcls)

        # Create object from new class, this super calls new from SatInfo and parent
        # class of calling class
        #Tracer()()
        obj = super(cls.__class__, newcls).__new__(newcls, sensor=sensor, satellite=satellite)
        obj.__init__()
        #print obj
        return obj


class SensorInfo(object):
    def __init__(self, satellite=None, sensor=None):
        # Pulled the attribute sets out of __init__ and put in separate
        # method
            #Set to str() to avoid issues with unicode
        self._set_SensorInfo_atts(satellite=str(satellite))
        # The super in SatSensorInfo is only calling SatInfo __init__
        # Not sure how to fix this, but for now, if we call _set_SensorInfo_atts
        # from SatInfo.__init__, we are covered (all SensorInfo methods are
        # reflected in the SatSensorInfo class, the __init__ just isn't called)
        # Just put the SatInfo version of this in SensorInfo class for
        # symmetry
        try:
            #Set to str() to avoid issues with unicode
            self._set_SatInfo_atts(sensor=str(sensor))
        except AttributeError:
            pass

#    @classmethod
    def _get_sensorname(self):
        for sensor in SensorInfo_classes.keys():
            #print SensorInfo_classes[sensor]
            #print self.__class__
            if issubclass(self.__class__, SensorInfo_classes[sensor]):
                return sensor

#    @classmethod
    def _set_SensorInfo_atts(self, satellite=None, **kwargs):
        #print 'Setting default SensorInfo attributes sat: ' + str(satellite)
        self.sensorname = self._get_sensorname()

        self.testsensorattr = 'hisensor!'

        self.cutofflength = 20
        self.swath_width_km = None
        self.num_lines = None
        self.num_samples = None

        self.OrigFName = {}
        self.OrigFName['base_dir'] = None
        self.OrigFName['pathnameformat'] = None
        self.OrigFName['pathfieldsep'] = None
        self.OrigFName['pathfillvalue'] = None
        self.OrigFName['noextension'] = False
        self.OrigFNames = [self.OrigFName]

        # *************MLS, the NOTE/CONVENTION is how it probably should work.
        #               for now we have to make date/time fields in path mathc
        #               datetime fields in filename. Should all go away with database.
        # NOTE: Datetime formats named date, time, dt0, dt1, dt2, dt3, dt4, dt5, or dt6 will be used in determining
        #       actual datetime for filename. Any other datetime formatted field (named dirdate, etc) will be included
        #       in datetime_fields (so will be populated correctly when recreating directory/filename), but will NOT
        #       be included in generating the actual datetime.
        # CONVENTION:
        #           Name datetime fields in FILENAME date, time, dt0, dt1, dt2, dt3, dt4, dt5, dt6
        #               MUST BE mutually exclusive (no overlap of format specifiers in those fields)
        #           Name datetime fields in DIRECTORYNAME dirdate, dirtime, dirdt0, etc
        #               DO NOT have to be mutually exclusive (these are just used for display purposes, not for
        #               determining actual datetime on filename object)
        # WAIT. Make that name directories date/time/dtx, and make them match EXACTLY with date/time/dtx
        #       in filename. Broke everything but wildcard filenames... Not worth making it work
        #       like above - should go away with database..
        standard_nameformat = '<date{%Y%m%d}>.<time{%H%M%S}>.<satname>.<sensorname>.<dataprovider>.<resolution>.<channel>.<producttype>.<area>.<extra>'

        self.LogFName = {}
        self.LogFName['cls'] = 'StandardDataFileName'
        self.LogFName['nameformat'] = standard_nameformat + '.<prefix>.<script>.<pid>.<timestamp>'
        self.LogFName['fieldsep'] = '.'
        self.LogFName['fillvalue'] = 'x'
        self.LogFName['pathnameformat'] = os.path.join(gpaths['LOGDIR'],
                     '<sensorname>', '<prefix>', '<date{%Y%m%d}>', '<area>')
        self.LogFName['pathfieldsep'] = '-'
        self.LogFName['pathfillvalue'] = 'x'
        self.LogFName['noextension'] = False

        self.ScratchFName = {}
        self.ScratchFName['cls'] = 'StandardDataFileName'
        self.ScratchFName['nameformat'] = standard_nameformat
        self.ScratchFName['fieldsep'] = '.'
        self.ScratchFName['fillvalue'] = 'x'
        self.ScratchFName['pathnameformat'] = os.path.join(gpaths['SCRATCH'],
                         'GeoIPS', '<satname>.<sensorname>.<dataprovider>',
                         '<date{%Y%m%d}>.<time{%H%M%S}>.<pid>',
                         '<producttype>.<subdir>.<timestamp>')
        self.ScratchFName['pathfieldsep'] = '.'
        self.ScratchFName['pathfillvalue'] = 'x'
        self.ScratchFName['noextension'] = False

        self.FName = {}
        self.FName['cls'] = 'StandardDataFileName'
        self.FName['nameformat'] = standard_nameformat
        self.FName['fieldsep'] = '.'
        self.FName['fillvalue'] = 'x'
        self.FName['noextension'] = False
        self.FName['runfulldir'] = False
        self.FName['default_producttype'] = None
        if self.sensorname and os.getenv('SATDATROOT'):
            #print 'setting base_dir in setSensorInfoAtts'
            self.FName['base_dirs'] = [os.path.join(os.getenv('SATDATROOT'),
                                          self.sensorname)]
        elif self.sensorname:
            self.FName['base_dirs'] = [os.path.join(gpaths['GEOIPS_OUTDIRS'],
                                       'data', self.sensorname)]
        else:
            self.FName['base_dirs'] = [os.path.join(gpaths['GEOIPS_OUTDIRS'],
                                       'data', 'undefined_sensorname')]
        self.FName['pathfieldsep'] = '-'
        self.FName['pathfillvalue'] = 'x'

        self.pathnameformat = '<date{%Y%m%d}>'

        self._set_sensor_atts()
        if None not in self.FName['base_dirs'] and self.pathnameformat is not None:
            # Set base_dir to first FName['base_dirs'], that will
            # always be the default
            self.base_dir = self.FName['base_dirs'][0]
            # If we are not an operational user and on an NRL box, add in XTUSER paths for files
            if not os.getenv('GEOIPS_OPERATIONAL_USER') and ('compute-0' in socket.gethostname() or socket.gethostname() in ['kauai.local']):
                for base_dir in self.FName['base_dirs']:
                    if os.getenv('SATDATROOT') and os.getenv('SATDATROOT') in base_dir and os.getenv('OpsSATDATROOT'):
                        self.FName['base_dirs'].append(base_dir.replace(os.getenv('SATDATROOT'), os.getenv('OpsSATDATROOT')))
                    if os.getenv('NPPDATA') and os.getenv('NPPDATA') in base_dir and os.getenv('OpsNPPDATA'):
                        self.FName['base_dirs'].append(base_dir.replace(os.getenv('NPPDATA'), os.getenv('OpsNPPDATA')))
            self.FName['pathnameformat'] = os.path.join('<base_dir>',
                                          self.pathnameformat)
        else:
            self.FName['pathnameformat'] = None
#        if satellite:
#            self._set_satellite_atts(satellite)

#    @classmethod
    def _set_sensor_atts(self):
        pass

#    @classmethod
#    def _set_satellite_atts(cls, satellite):
#
#        try:
#            satinfo = SatInfo_classes[satellite](sensor=cls.sensorname)
#        except KeyError:
#            raise SatInfoError('Invalid satellite \'' + str(satellite) + '\' not defined in SatInfo_classes')
#        except SatInfoError:
#            raise
#
#        cls._set_satellite_att(satinfo, 'orbital_period')
#        cls._set_satellite_att(satinfo, 'tle_name')
#        cls._set_satellite_att(satinfo, 'tscan_name')
#
#        cls.satname = satellite
#
#        return
#
#    @classmethod
#    def _set_satellite_att(cls, satinfo, att):
#        if not hasattr(cls, att):
#            try:
#                setattr(cls, att, getattr(satinfo, att))
#            except AttributeError:
#                setattr(cls, att, None)


class AMSUASensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        ''' Specify which filename format in datafilename
        this sensor uses.
        NPR.AAOP.NN.D13344.S1426.E1614.B4409596.NS
        NPR.MHOP.M1.D13344.S1703.E1758.B0637980.NS
        3rd field: NK NOAA-15
                    NL NOAA-16
                    NM NOAA-17
                    NN NOAA-18
                    NP NOAA-19
                    M2 METOP-2/A
        2nd field:  AAOP: AMSU-A
                    ABOP: AMSU-B
                    MHOP: AMSU-B
        '''
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        self.OrigFName['cls'] = 'AMSUFileName'
        self.OrigFName['nameformat'] = '<npr>.<sensor>.<satellite>.<date{D%y%j}>.<time{S%H%M}>.<endtime>.<btime>'
        self.OrigFName['fieldsep'] = '.'
        self.OrigFName['fillvalue'] = 'x'
        self.OrigFNames = [self.OrigFName]
        self.swath_width_km = 2200
        #self.num_lines = 2030
        #self.num_samples = 1354
        self.mins_per_file = 5
        self.pathnameformat = '<date{%Y%m%d}>'


class AMSUBSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        ''' Specify which filename format in datafilename
        this sensor uses.
        NPR.AAOP.NN.D13344.S1426.E1614.B4409596.NS
        NPR.MHOP.M1.D13344.S1703.E1758.B0637980.NS
        3rd field: NK NOAA-15
                    NL NOAA-16
                    NM NOAA-17
                    NN NOAA-18
                    NP NOAA-19
                    M2 METOP-2/A
        2nd field:  AAOP: AMSU-A
                    ABOP: AMSU-B
                    MHOP: AMSU-B
        '''
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        self.OrigFName['cls'] = 'AMSUFileName'
        self.OrigFName['nameformat'] = '<npr>.<sensor>.<satellite>.<date{D%y%j}>.<time{S%H%M}>.<endtime>.<btime>'
        self.OrigFName['fieldsep'] = '.'
        self.OrigFName['fillvalue'] = 'x'
        self.OrigFNames = [self.OrigFName]
        self.swath_width_km = 2200
        #self.num_lines = 2030
        #self.num_samples = 1354
        self.mins_per_file = 5
        self.pathnameformat = '<date{%Y%m%d}>'


class AMSR2SensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        #AMSR2-PRECIP_v1r0_GW1_s201506291440230_e201506291619210_c201506292006200.nc
        #AMSR2-OCEAN_v1r0_GW1_s201506291440230_e201506291619210_c201506292006200.nc
        #AMSR2-MBT_v1r0_GW1_s201506291440230_e201506291619210_c201506292006200.nc
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        self.OrigFName['cls'] = 'AMSR2FileName'
        # #! Only works to remove characters from the end of a datetime format string!
        #    don't use it in the middle of the string unless you fix the code in utils.path.filename.py!!
        self.OrigFName['nameformat'] = '<amsr2prod>_<vers>_<satname>_<date{s%Y%m%d%H%M%S%!}>_<endtime>_<creationtime>'
        self.OrigFName['fieldsep'] = '_'
        self.OrigFName['fillvalue'] = 'x'
        self.pathnameformat = os.path.join('<ext>','<producttype>')
        self.OrigFNames = [self.OrigFName]
        # Defaults to SATDATROOT/<sensorname>, don't need to set.
        #self.FName['base_dirs'] = [os.path.join(os.getenv('SATDATROOT'), 'amsr2')]
        self.FName['default_producttype'] = 'mbt'
        self.swath_width_km = 1450
        #self.num_lines = 2030
        #self.num_samples = 1354
        self.mins_per_file = 98
        self.interpolation_radius_of_influence = 10000


class AMSRESensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # Probably want to do something about this - currently Errors if mins_per_file
        # is not defined for polar orbiters, when trying to use pass_prediction for merging
        # granules. mins_per_file doesn't even make sense, since it can vary...
        self.mins_per_file = 10


class ASCATSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # pull/ascat_20150628_235700_metopb_14410_srv_o_250_ovw.l2_bin
        # $SATDATROOT/scat/ascat/metopa/ascii/primary/12p5km/
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        self.OrigFName['cls'] = 'ASCATFileName'
        self.OrigFName['nameformat'] = '<ascat>_<date{%Y%m%d}>_<time{%H%M%S}>_<satname>_<num1>_<srv>_<o>_<res>_<ovw>'
        self.OrigFName['fieldsep'] = '_'
        self.OrigFName['fillvalue'] = 'x'
        self.OrigFNames = [self.OrigFName]
        self.swath_width_km = 500
        #self.num_lines = 2030
        #self.num_samples = 1354
        self.mins_per_file = 3
        self.pathnameformat = '<resolution>'


class ATMSSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        self.OrigFName['cls'] = 'NPPFileName'
        self.OrigFName['nameformat'] = '<datatype>_<satname>_<date{d%Y%m%d}>_<time{t%H%M%S%f}>_<endtime>_<orbitnum>_<creationtime>_<dataoriginator>_<datalevel>'
        self.OrigFName['fieldsep'] = '_'
        self.OrigFName['fillvalue'] = 'x'
        # SATMS_npp_d20150831_t1741316_e1742033_b19910_fnmoc_dev.h5
        OrigFName2 = self.OrigFName.copy()
        OrigFName2['cls'] = 'NPPFileName'
        OrigFName2['nameformat'] = '<datatype>_<satname>_<date{d%Y%m%d}>_<time{t%H%M%S%f}>_<endtime>_<orbitnum>_<dataoriginator>_<datalevel>'
        OrigFName2['fieldsep'] = '_'
        OrigFName2['fillvalue'] = 'x'
        OrigFName2['noextension'] = False
        if os.getenv('FROMBERYLDIR'):
            OrigFName2['base_dir'] = os.getenv('FROMBERYLDIR')
        else:
            OrigFName2['base_dir'] = os.path.join(gpaths['GEOIPS_OUTDIRS'],
                                                  'npp','atms')
        self.OrigFNames = [self.OrigFName, OrigFName2]

        sdr_geo = ['GATMO']
        sdr_data = ['SATMS']

        tdr_geo = ['GATMO']
        tdr_data = ['TATMS']

        self.prefixes = {'sdr': sdr_geo + sdr_data,
                         'tdr': tdr_geo + tdr_data}

        self.all_prefixes = []

        for filetype in self.prefixes:
            self.all_prefixes += self.prefixes[filetype]

        self.all_prefixes = set(self.all_prefixes)

        self.swath_width_km = 2503
        self.num_lines = 12
        self.num_samples = 96
        self.mins_per_file = 1
        if os.getenv('NPPDATA'):
            self.FName['base_dirs'] = [os.path.join(os.getenv('NPPDATA'),'atms')]
        self.pathnameformat = os.path.join('<dataprovider>-<ext>',
                                           '<date{%Y%m%d}>',
                                           '<time{%H%M%S}>')

class CLAVRXSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        #goes15_2016_310_1800.level2.hdf
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        self.OrigFName['cls'] = 'CLAVRXFileName'
        self.OrigFName['nameformat'] = '<satname>_<dt0{%Y}>_<dt1{%j}>_<dt2{%H%M.%!%!%!%!%!%!}>' 
        self.OrigFName['fieldsep'] = '_'
        self.OrigFName['fillvalue'] = 'x'
        self.OrigFName['noextension'] = False
        self.OrigFNames = [self.OrigFName]
        self.interpolation_radius_of_influence = 75000

class CCBGSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        self.OrigFName['cls'] = 'CCBGFileName'
        self.OrigFName['nameformat'] = '<satname>_<sensorname>_<dt0{%Y}>_<dt1{%j}>_<dt2{%H%M_%!%!%!%!%!%!%!_%!%!}>' 
        self.OrigFName['fieldsep'] = '_'
        self.OrigFName['fillvalue'] = 'x'
        self.OrigFName['noextension'] = False
        self.OrigFNames = [self.OrigFName]
        self.interpolation_radius_of_influence = 75000

class GMISensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        #NRTPUB/GMI1B/1B.GPM.GMI.TB2014.20150628-S182142-E182640.V03C.RT-H5
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        self.OrigFName['cls'] = 'GPMFileName'
        # #! Only works to remove characters from the end of a datetime format string!
        #    don't use it in the middle of the string unless you fix the code in utils.path.filename.py!!
        self.OrigFName['nameformat'] = '<level>.<satname>.<sensorname>.<product>.<date{%Y%m%d-S%H%M%S-E%!%!%!%!%!%!}>.<version>.<exttype>'
        self.OrigFName['fieldsep'] = '.'
        self.OrigFName['fillvalue'] = 'x'
        self.OrigFName['noextension'] = True
        self.pathnameformat = os.path.join('<channel>','<date{%Y%m%d}>')
        OrigFName1 = self.OrigFName.copy()
        OrigFName1['cls'] = 'GPMFileName'
        # #! Only works to remove characters from the end of a datetime format string!
        #    don't use it in the middle of the string unless you fix the code in utils.path.filename.py!!
        OrigFName1['nameformat'] = '<level>.<satname>.<sensorname>.<product>.<date{%Y%m%d-S%H%M%S-E%!%!%!%!%!%!}>.<mins>.<version>.<exttype>'
        self.OrigFNames = [self.OrigFName, OrigFName1]
        self.swath_width_km = 904
        #self.num_lines = 2030
        #self.num_samples = 1354
        self.mins_per_file = 5
        # self.FName defaults to None if SATDATROOT not defined.
        if os.getenv('SATDATROOT'):
            self.FName['base_dirs'] = [os.path.join(os.getenv('SATDATROOT'),
                                          'gpm')]
        self.interpolation_radius_of_influence = 10000

class GLMSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        self.interpolation_radius_of_influence = 10000
        self.mins_per_file = 10
        self.LogFName['pathnameformat'] = os.path.join(gpaths['LOGDIR'],
                     '<sensorname>',
                     '<prefix>',
                     '<date{%Y%m%d}>',
                     'all')
        self.OrigFName['cls'] = 'ABIFileName'
        # OR_ABI-L1b-RadF-M3C02_G16_s20170642036100_e20170642046467_c20170642046500.nc
        # OR_ABI-L1b-RadC-M3C03_G16_s20171070042189_e20171070044562_c20171070045005.nc
        # OR_SEIS-L1b-EHIS_G16_s20170622315250_e20170622315250_c20170622320253.nc
        # OR_GLM-L2-LCFA_G16_s20173221230000_e20173221230200_c20173221230226.nc
        self.OrigFName['nameformat'] = '<or>_<sensornamelevelprodtypescantype>_<satname>_<date{%!%Y%j%H%M%S%!}>_<enddt>_<createdt>'
        self.OrigFName['fieldsep'] = '_'
        self.OrigFName['fillvalue'] = 'x'
        self.OrigFName['pathfieldsep'] = '-'
        self.OrigFName['pathfillvalue'] = 'x'
        self.OrigFName['noextension'] = False
        self.OrigFNames = [self.OrigFName]


class GPROFSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # MOD021KM.P2014290.0415.hdf
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        OrigFName = self.OrigFName.copy()
        OrigFName['cls'] = 'GPMFileName'
        # #! Only works to remove characters from the end of a datetime format string!
        #    don't use it in the middle of the string unless you fix the code in utils.path.filename.py!!
        self.OrigFName['nameformat'] = '<level>.<satname>.<sensorname>.<algyear>.<date{%Y%m%d-S%H%M%S-E%!%!%!%!%!%!}>.<version>.<exttype>'
        self.pathnameformat = os.path.join('<channel>','<date{%Y%m%d}>')
        OrigFName['fieldsep'] = '.'
        OrigFName['fillvalue'] = 'x'
        OrigFName['noextension'] = True
        self.OrigFNames = [self.OrigFName]
        self.swath_width_km = 904
        #self.num_lines = 2030
        #self.num_samples = 1354
        self.mins_per_file = 5
        # self.FName set in SensorInfo class above if SATDATROOT not defined.
        if os.getenv('SATDATROOT'):
            self.FName['base_dirs'] = [os.path.join(os.getenv('SATDATROOT'),
                                      'gpm')]


class GOESImagerSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # MOD021KM.P2014290.0415.hdf
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        OrigFNameDish = self.OrigFName.copy()
        OrigFNameDish2 = self.OrigFName.copy()
        OrigFNameDishNC = self.OrigFName.copy()
        OrigFNameCLASS = self.OrigFName.copy()

        OrigFNameDish['cls'] = 'GOESFileName'
        OrigFNameDish['nameformat'] = '<date{%Y%m%d}>.<time{%H%M}>.<satname>'
        OrigFNameDish['fieldsep'] = '.'
        OrigFNameDish['fillvalue'] = 'x'
        OrigFNameDish['noextension'] = True

        OrigFNameDish2['cls'] = 'GOESFileName'
        OrigFNameDish2['nameformat'] = '<date{%Y%m%d}>.<time{%H%M%S}>.<satname>'
        OrigFNameDish2['fieldsep'] = '.'
        OrigFNameDish2['fillvalue'] = 'x'
        OrigFNameDish2['noextension'] = True

        OrigFNameDishNC['cls'] = 'GOESFileName'
        OrigFNameDishNC['nameformat'] = '<date{%Y%m%d}>.<time{%H%M}>.<satname>.<dataset>'
        OrigFNameDishNC['fieldsep'] = '.'
        OrigFNameDishNC['fillvalue'] = 'x'
        OrigFNameDishNC['noextension'] = False

        OrigFNameCLASS['cls'] = 'GOESCLASSFileName'
        OrigFNameCLASS['nameformat'] = '<satname>.<year{%Y}>.<doy{%j}>.<time{%H%M%S}>.<band>'
        OrigFNameCLASS['fieldsep'] = '.'
        OrigFNameCLASS['fillvalue'] = 'x'

        self.pathnameformat = os.path.join('<satname>','<date{%Y%m%d.%H%M}>')
        # This tells the downloader and process_overpass to kick off processing on
        # the directory name, not the full filename.
        self.FName['runfulldir'] = True
        self.swath_width_km = 12000
        self.mins_per_file = 10

        # This is probably not true for all of the data types.
        # If we pass a directory, it will run on the directory, but
        # I don't think we want to run on the directory if we pass a
        # single file.
        #self.FName['runfulldir'] = True
        #self.swath_width_km = 904
        #self.num_lines = 2030
        #self.num_samples = 1354
        #self.mins_per_file = 5
        #self.FName['base_dirs'] = [os.getenv('SATDATROOT') + '/goes-west/hires']
        #self.pathnameformat = ''
        # This is used in scifile/containers.py register. Has to match biggest possible
        # pixel size (at edge of scan)
        self.interpolation_radius_of_influence = 15000
        self.OrigFNames = [OrigFNameDish, OrigFNameDish2, OrigFNameDishNC, OrigFNameCLASS]


class ABISensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        #######################################################################
        # Defaults for these attributes can be found in the
        # _set_SensorInfo_atts method of the SensorInfo class
        # above
        #######################################################################

        #######################################################################
        # Specify sensor-specific attributes
        #######################################################################

        self.swath_width_km = 12000
        self.interpolation_radius_of_influence = 10000
        self.mins_per_file = 10



        #######################################################################
        # Specify any special formatting for the automated log filename / path
        #######################################################################

        # The default Log pathnameformat includes "area", which we don't want, so override log path here.
        self.LogFName['pathnameformat'] = os.path.join(gpaths['LOGDIR'],
                                     '<sensorname>','<prefix>',
                                     '<date{%Y%m%d}>','all')


        #######################################################################
        # Specify the parsing for the original sensor filename,
        # and where the original files can be found.
        #######################################################################

        # This is the class name found in utils/path/datafilename.py
        # self.OrigFName['cls'] specifies how to use the 'nameformat' fields in
        # the original filename to create the internal GeoIPS standard formatted
        # filename / path.
        self.OrigFName['cls'] = 'ABIFileName'
        # OR_ABI-L1b-RadF-M3C02_G16_s20170642036100_e20170642046467_c20170642046500.nc
        # OR_ABI-L1b-RadC-M3C03_G16_s20171070042189_e20171070044562_c20171070045005.nc
        # OR_SEIS-L1b-EHIS_G16_s20170622315250_e20170622315250_c20170622320253.nc
        self.OrigFName['nameformat'] = '<or>_<sensornamelevelprodtypescantype>_<satname>_<date{%!%Y%j%H%M%S%!}>_<enddt>_<createdt>'
        self.OrigFName['fieldsep'] = '_'
        self.OrigFName['fillvalue'] = 'x'
        self.OrigFName['pathfieldsep'] = '-'
        self.OrigFName['pathfillvalue'] = 'x'
        self.OrigFName['noextension'] = False
        # For downloader
        self.OrigFName['prefix_search_string'] = 'OR_'
        self.OrigFName['postfix_search_string'] = '.nc'
        # self.OrigFName['base_dir'] is where the original files show up - this is where
        # downloader looks for them.
        # DO NOT specify OrigFName1['pathnameformat']  if you want DataFileName to
        # just match files directly in OrigFName1['base_dir']
        if os.getenv('BIGDATA'):
            self.OrigFName['base_dir'] = os.path.join(os.getenv('BIGDATA'),
                                                      'incoming')
        else:
            # USER_OUTDIRS must always be defined.
            self.OrigFName['base_dir'] = os.path.join(gpaths['GEOIPS_OUTDIRS'],
                                          'data', 'incoming')

        # If there are multiple possible OrigFNames, list them in self.OrigFNames
        # DataFileName loops through all self.OrigFNames when trying to match.
        self.OrigFNames = [self.OrigFName]



        #######################################################################
        # Specify the final GeoIPS formatted filename attributes.
        #######################################################################

        # Files end up in self.FName['base_dirs']/self.pathnameformat
        # The list of base_dirs is used to automatically find files in process_overpass.py,
        # and self.FName['base_dirs'][0] is the "primary" location where the
        # downloader automatically puts files.
        self.pathnameformat = os.path.join('<satname>', '<sensorname>',
                                           '<area>', '<date{%Y%m%d}>',
                                           '<date{%H%M%S}>')
        if os.getenv('OpsBIGDATA'):
            self.FName['base_dirs'] = [os.getenv('BIGDATA'), os.getenv('OpsBIGDATA')]
        elif os.getenv('BIGDATA'):
            self.FName['base_dirs'] = [os.getenv('BIGDATA')]
        # This tells the downloader and process_overpass to kick off processing on
        # the directory name, not the full filename.
        self.FName['runfulldir'] = True


class AHISensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        # 20150617_0250/HS_H08_20150617_0250_B12_FLDK_R20_S0510.DAT.bz2
        #print 'AHISensorInfo'
        # This doesn't transfer well - %H%M for path, %H%M%S for filename. when creating dfn, does not
        # create exact same filename...
        # New convention - make formats of date/time fields in paths EXACTLY the same as date/time fields in
        # filenames...
        self.pathnameformat = os.path.join('<dataprovider>',
                                           '<date{%Y%m%d}>',
                                           '<time{%H%M%S}>')

        self.LogFName['pathnameformat'] = os.path.join(gpaths['LOGDIR'],
                                                 '<sensorname>',
                                                 '<prefix>',
                                                 '<date{%Y%m%d}>',
                                                 'all')

        OrigFName1 = self.OrigFName.copy()
        OrigFName1['cls'] = 'AHIDATFileName'
        OrigFName1['nameformat'] = '<hs>_<satname>_<date{%Y%m%d}>_<time{%H%M}>_<channel>_<scansize>_<resolution>_<slice>'
        OrigFName1['fieldsep'] = '_'
        OrigFName1['fillvalue'] = 'x'
        OrigFName1['pathfieldsep'] = '-'
        OrigFName1['pathfillvalue'] = 'x'
        OrigFName1['noextension'] = False
        if os.getenv('AHIDATA'):
            OrigFName1['base_dir'] = os.getenv('AHIDATA')
        else:
            # USER_OUTDIRS must always be defined.
            OrigFName1['base_dir']  =  os.path.join(gpaths['GEOIPS_OUTDIRS'],
                                                  'data', 'himawari', 'ahi')
        OrigFName1['pathnameformat'] = os.path.join('<base_dir>',
                                                  self.pathnameformat)

        OrigFName2 = self.OrigFName.copy()
        OrigFName2['cls'] = 'AHIHPCtgzFileName'
        OrigFName2['nameformat'] = '<date{%Y%m%d}>_<time{%H%M}>'
        OrigFName2['fieldsep'] = '_'
        OrigFName2['fillvalue'] = 'x'
        OrigFName2['pathfieldsep'] = '-'
        OrigFName2['pathfillvalue'] = 'x'
        OrigFName2['noextension'] = False
        if os.getenv('FTPROOT'):
            OrigFName2['base_dir'] = os.path.join(os.getenv('FTPROOT'),
                                                  'satdata', 'himawari')
        else:
            OrigFName2['base_dir'] = os.path.join(gpaths['GEOIPS_OUTDIRS'], 
                                                  'data', 'himawari', 'ahi')
        OrigFName2['pathnameformat'] = '<base_dir>'

        OrigFName3 = self.OrigFName.copy()
        OrigFName3['cls'] = 'StandardDataFileName'
        OrigFName3['nameformat'] = '<date{%Y%m%d}>.<time{%H%M%S}>.<satname>.<sensorname>.<dataprovider>.<resolution>.<channel>.<producttype>.<area>.<extra>'
        OrigFName3['fieldsep'] = '.'
        OrigFName3['fillvalue'] = 'x'
        OrigFName3['pathfieldsep'] = '-'
        OrigFName3['pathfillvalue'] = 'x'
        OrigFName3['noextension'] = False
        if os.getenv('AHIDATA'):
            OrigFName3['base_dir'] = os.getenv('AHIDATA')
        else:
            # USER_OUTDIRS must always be defined.
            OrigFName3['base_dir'] = os.path.join(gpaths['GEOIPS_OUTDIRS'],
                                                  'data', 'himawari', 'ahi')
        OrigFName3['pathnameformat'] = os.path.join('<base_dir>',
                                                      self.pathnameformat)

        self.swath_width_km = 12000
        self.mins_per_file = 10

        # For testing purposes, make the moves go faster...
        #OrigFName2['base_dir'] = os.getenv('NPPDATA') + '/himawari_in'
        #self.swath_width_km = 904
        #self.num_lines = 2030
        #self.num_samples = 1354
        #self.mins_per_file = 5
        # This is used in scifile/containers.py register. Has to match biggest possible
        # pixel size (at edge of scan)
        self.interpolation_radius_of_influence = 4000
        #self.OrigFNames = [OrigFName1, OrigFName2]
        self.OrigFNames = [OrigFName2, OrigFName1, OrigFName3]
        self.OrigFName = OrigFName3
        if os.getenv('OpsAHIDATA'):
            self.FName['base_dirs'] = [os.getenv('AHIDATA'), os.getenv('OpsAHIDATA')]
        elif os.getenv('AHIDATA'):
            self.FName['base_dirs'] = [os.getenv('AHIDATA')]
        self.FName['runfulldir'] = True
        # These are from standard datafilename. Slice becomes area


class JAMISensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        self.OrigFName['cls'] = 'JAMITDFFileName'
        self.OrigFName['nameformat'] = '<date{%Y%m%d}>.<time{%H%M}>.<resolution>.<satname>'
        self.OrigFName['fieldsep'] = '.'
        self.OrigFName['fillvalue'] = 'x'
        self.OrigFName['noextension'] = True
        OrigFName2 = self.OrigFName.copy()
        OrigFName2['cls'] = 'JAMIBFTTDFXFileName'
        OrigFName2['nameformat'] = '<date{%Y%m%d}>.<time{%H%M}>.<satname>'
        OrigFName2['fieldsep'] = '.'
        OrigFName2['fillvalue'] = 'x'
        OrigFName2['noextension'] = False
        OrigFName3 = self.OrigFName.copy()
        OrigFName3['cls'] = 'FNMOCBFTGSFileName'
        OrigFName3['nameformat'] = '<satname>_<date{%j%H%M}>_<producttype>'
        OrigFName3['fieldsep'] = '_'
        OrigFName3['fillvalue'] = 'x'
        OrigFName3['noextension'] = False
        self.OrigFNames = [self.OrigFName, OrigFName2, OrigFName3]
        #self.swath_width_km = 904
        #self.num_lines = 2030
        #self.num_samples = 1354
        #self.mins_per_file = 5
        # This is used in scifile/containers.py register. Has to match biggest possible
        # pixel size (at edge of scan)
        self.interpolation_radius_of_influence = 10000
        # Go with the default here - no longer need to conform with old directory structure
        #self.FName['base_dirs'] = [os.getenv('SATDATROOT') + '/gms-6/hires']
        self.pathnameformat = ''


class MINTSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        self.interpolation_radius_of_influence = 15000


class MODISSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # MOD021KM.P2014290.0415.hdf
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        OrigFName = self.OrigFName.copy()
        OrigFName2 = self.OrigFName.copy()
        OrigFName3 = self.OrigFName.copy()
        OrigFName['cls'] = 'MODISFileName'
        OrigFName['nameformat'] = '<datatype>.<date{A%Y%j}>.<time{%H%M}>'
        OrigFName['fieldsep'] = '.'
        OrigFName['fillvalue'] = 'x'
        OrigFName2['cls'] = 'MODISFileName'
        OrigFName2['nameformat'] = '<datatype>.<date{P%Y%j}>.<time{%H%M}>'
        OrigFName2['fieldsep'] = '.'
        OrigFName2['fillvalue'] = 'x'
        OrigFName3['cls'] = 'MODISFileName'
        OrigFName3['nameformat'] = '<datatype>.<date{A%Y%j}>.<time{%H%M}>.<num>.<nrt>'
        OrigFName3['fieldsep'] = '.'
        OrigFName3['fillvalue'] = 'x'
        self.OrigFNames = [OrigFName, OrigFName2, OrigFName3]
        self.FName['runfulldir'] = True
        # Slowly increasing this until the lines between granules go away.  Started at 1500, then 2000, 2500
        # This is used in scifile/containers.py register. Has to match biggest possible
        # pixel size (at edge of scan)
        self.interpolation_radius_of_influence = 4500
        self.swath_width_km = 3000
        self.num_lines = 2030
        self.num_samples = 1354
        self.mins_per_file = 5
        self.pathnameformat = os.path.join('<dataprovider>', 
                                           '<satname>',
                                           '<date{%Y%m%d}>',
                                           '<time{%H%M%S}>')


class NAVGEMForecastSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        self.OrigFName['cls'] = 'NAVGEMFileName'
        self.OrigFName['nameformat'] = 'flatfiles_<resolution>_<date{%Y%m%d%H}>_<tau>'
        self.OrigFName['fieldsep'] = '_'
        self.OrigFName['fillvalue'] = 'x'
        self.OrigFNames = [self.OrigFName]
        #self.num_lines = 2030
        #self.num_samples = 1354
        self.mins_per_file = 60
        #self.FName['base_dirs'] = [os.getenv('SATDATROOT') + '/amsub/global']
        #self.pathnameformat = ''

class WINDSSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        self.interpolation_radius_of_influence = 56000
        #### This must match appropriate DataFileName class name in utils/path/datafilename.py
        #### AMV201803121100GOESE.txt  AMV201803121300GOESEO.txt  QI2018031205TPARC-OCEAN.txt  QI2018031205WG10H.txt  QI2018031205WVM5H.txt
        ###OrigFName = self.OrigFName.copy()
        ###OrigFName['cls'] = 'NOAADMVTxtFileName'
        ###OrigFName['nameformat'] = '<stuff1>'
        ###OrigFName['fieldsep'] = '_'
        ###OrigFName['fillvalue'] = 'x'
        ###OrigFName['noextension'] = False
        ###self.OrigFNames = [OrigFName]
        ###self.FName['runfulldir'] = True
        ###if os.getenv('SATDATROOT'):
        ###    #print 'setting base_dir in setSensorInfoAtts'
        ###    self.FName['base_dirs'] = [os.getenv('SATDATROOT')]
        #### resolution is the tau, extra is the level
        ###self.pathnameformat = '<satname>/<sensorname>/<date{%Y%m%d}>'
        ####self.num_lines = 2030
        ####self.num_samples = 1354
        ####self.mins_per_file = 60
        ####self.FName['base_dirs'] = [os.getenv('SATDATROOT') + '/amsub/global']
        ####self.pathnameformat = ''


class MODELSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        self.interpolation_radius_of_influence = 56000
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        # US058GCOM-GR1mdl.0018_0056_03300F0OF2017020206_0001_000000-000000grnd_sea_temp
        # US058GCOM-GR1dyn.COAMPS-NEPAC_NEPAC-n2-a1_01800F0NL2017010112_0001_000000-000000grnd_sea_temp
        OrigFName = self.OrigFName.copy()
        OrigFName2 = self.OrigFName.copy()
        OrigFName3 = self.OrigFName.copy()
        OrigFName4 = self.OrigFName.copy()
        OrigFName['cls'] = 'NAVGEMGribFileName'
        OrigFName['nameformat'] = '<stuff1>_<stuff2>_<date{%!%!%!%!%!%!%!%!%!%Y%m%d%H}>_<stuff3>_<product1>_<product2>'
        OrigFName['fieldsep'] = '_'
        OrigFName['fillvalue'] = 'x'
        OrigFName['noextension'] = True
        OrigFName2['cls'] = 'NAVGEMGribFileName'
        OrigFName2['nameformat'] = '<stuff1>_<stuff2>_<date{%!%!%!%!%!%!%!%!%!%Y%m%d%H}>_<stuff3>_<product1>_<product2>_<product3>'
        OrigFName2['fieldsep'] = '_'
        OrigFName2['fillvalue'] = 'x'
        OrigFName2['noextension'] = True
        OrigFName3['cls'] = 'NAVGEMGribFileName'
        OrigFName3['nameformat'] = '<stuff1>_<stuff2>_<date{%!%!%!%!%!%!%!%!%!%Y%m%d%H}>_<stuff3>_<product1>_<product2>_<product3>_<product4>'
        OrigFName3['fieldsep'] = '_'
        OrigFName3['fillvalue'] = 'x'
        OrigFName3['noextension'] = True
        OrigFName4['cls'] = 'NAVGEMGribFileName'
        OrigFName4['nameformat'] = '<stuff1>_<stuff2>_<date{%!%!%!%!%!%!%!%!%!%Y%m%d%H}>_<stuff3>_<product1>'
        OrigFName4['fieldsep'] = '_'
        OrigFName4['fillvalue'] = 'x'
        OrigFName4['noextension'] = True
        self.OrigFNames = [OrigFName, OrigFName2, OrigFName3, OrigFName4]
        self.FName['runfulldir'] = True
        if os.getenv('SATDATROOT'):
            #print 'setting base_dir in setSensorInfoAtts'
            self.FName['base_dirs'] = [os.getenv('SATDATROOT')]
        # resolution is the tau, extra is the level
        self.pathnameformat = os.path.join('<satname>', '<sensorname>',
                                           '<area>','<date{%Y%m%d%H}>',
                                           '<resolution>-<extra>')
        #self.num_lines = 2030
        #self.num_samples = 1354
        #self.mins_per_file = 60
        #self.FName['base_dirs'] = [os.getenv('SATDATROOT') + '/amsub/global']
        #self.pathnameformat = ''

class ICAPSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # /shared/aerosol_maud1/users/sessions/products/ICAP/201711/
        # icap_2017110500_aod.nc
        self.interpolation_radius_of_influence = 56000
        OrigFName = self.OrigFName.copy()
        OrigFName['cls'] = 'ICAPFileName'
        OrigFName['nameformat'] = '<icap>_<date{%Y%m%d%H}>_<prod>'
        OrigFName['fieldsep'] = '_'
        OrigFName['fillvalue'] = 'x'
        if os.getenv('ICAPDATA'):
            OrigFName['base_dir'] = os.getenv('ICAPDATA')
        else:
            OrigFName['base_dir'] = gpaths['GEOIPS_OUTDIRS'] + '/data/model/icap'
        self.OrigFNames = [OrigFName]
        self.pathnameformat = ''

class NAAPSAOTSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        self.interpolation_radius_of_influence = 56000
        self.pathnameformat = ''
        self.mins_per_file = 30

class OLSSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        # RS_S2B00563.20143021221
        #self.OrigFName['cls'] = 'RSCATFileName'
        #self.OrigFName['nameformat'] = 'datatype_YYYYJJJHHMN'
        #self.OrigFName['fieldsep'] = '_'
        #self.OrigFName['fillvalue'] = 'x'
        self.swath_width_km = 3000
        self.mins_per_file = 30
        # Go with the default - no longer need to conform to old directory structure
        #self.FName['base_dirs'] = [os.getenv('SATDATROOT') + '/ols/global']
        self.pathnameformat = ''
        #self.data_types = {}


class OSCATSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        #self.OrigFName['fillvalue'] = 'x'
        #self.swath_width_km = 904
        #self.num_lines = 2030
        #self.num_samples = 1354
        #self.mins_per_file = 5
        # oscat_20170913_102336_scasa1_05107_o_250_2104_ovw_l2.nc
        OrigFNameOSCATKNMI25 = self.OrigFName.copy()
        OrigFNameOSCATKNMI25['cls'] = 'OSCATKNMI25FileName'
        OrigFNameOSCATKNMI25['nameformat'] = '<oscat>_<date{%Y%m%d}>_<time{%H%M%S}>_<shortsat>_' + \
                                             '<rev>_<type>_<resolution>_<vers>_<cont>_<level>'
        OrigFNameOSCATKNMI25['fieldsep'] = '_'
        OrigFNameOSCATKNMI25['fillvalue'] = 'x'
        OrigFNameOSCATKNMI25['noextension'] = False
        self.OrigFNames = [OrigFNameOSCATKNMI25]
        self.pathnameformat = '<resolution>'


class RSCATSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        # rs_l2b_v1_01294_201412151320.nc.gz
        # Have to specify that there is no extension so FileName doesn't break
        # outer is 1100km
        self.mins_per_file = 100
        self.swath_width_km = 900
        self.data_types = {}

        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        # RS_S2B00563.20143021221
        OrigFNameRSCAT25 = self.OrigFName.copy()
        OrigFNameRSCAT12p5 = self.OrigFName.copy()

        OrigFNameRSCAT12p5['cls'] = 'RSCATFileName'
        OrigFNameRSCAT12p5['nameformat'] = '<rs>_<prodtype>_<vers>_<revnum>_<date{%Y%m%d%H%M}>'
        OrigFNameRSCAT12p5['fieldsep'] = '_'
        OrigFNameRSCAT12p5['fillvalue'] = 'x'

        OrigFNameRSCAT25['cls'] = 'RSCAT25FileName'
        OrigFNameRSCAT25['nameformat'] = '<RS_datatyperevnum>.<date{%Y%j%H%M}>'
        OrigFNameRSCAT25['fieldsep'] = '.'
        OrigFNameRSCAT25['fillvalue'] = 'x'
        # Have to specify that there is no extension so FileName doesn't break
        OrigFNameRSCAT25['noextension'] = True

        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        # rapid_20160523_181659_iss____09461_2hr_o_250_1903_ovw_l2.nc
        OrigFNameRSCATKNMI25 = self.OrigFName.copy()
        OrigFNameRSCATKNMI25['cls'] = 'RSCATKNMI25FileName'
        OrigFNameRSCATKNMI25['nameformat'] = '<rapid>_<date{%Y%m%d}>_<time{%H%M%S}>_<sat>_' + \
                                           '<blank>_<blank>_<blank>_<rev>_<srv>_<type>_' + \
                                           '<resolution>_<vers>_<contents>_<level>'
        OrigFNameRSCATKNMI25['fieldsep'] = '_'
        OrigFNameRSCATKNMI25['fillvalue'] = 'x'
        OrigFNameRSCATKNMI25['noextension'] = False
        self.OrigFNames = [OrigFNameRSCAT25, OrigFNameRSCAT12p5, OrigFNameRSCATKNMI25]
        self.pathnameformat = '<resolution>'


class SAPHIRSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        # MT1SAPSL1A__1.07_000_1_17_I_2015_08_31_05_13_46_2015_08_31_07_07_31_20047_20049_207_66_68_BL1_00.h5
        OrigFName = self.OrigFName.copy()
        OrigFName['cls'] = 'MeghaTropiquesFileName'
        OrigFName['nameformat'] = '<satsensorlevel>_<blank>_<vers>_<num1>_<num2>_<num3>_' + \
                                '<let1>_<dt0{%Y}>_<dt1{%m}>_<dt2{%d}>_' + \
                                '<dt3{%H}>_<dt4{%M}>_<dt5{%S}>_<enddate1>' + \
                                '_<enddate2>_<enddate3>_<endtime1>_<endtime2>_' + \
                                '<endtime3>_<num4>_<num5>_<num6>_<num7>_' + \
                                '<num8>_<let2>_<num9>'

        OrigFName['fieldsep'] = '_'
        OrigFName['fillvalue'] = 'x'
        if os.getenv('FTPROOT'):
            OrigFName['base_dir'] = os.getenv('FTPROOT') + '/satdata/gsfc'
        else:
            OrigFName['base_dir'] = gpaths['GEOIPS_OUTDIRS'] + '/data/meghatropiques/saphir'
        self.OrigFNames = [OrigFName]
        # Go with the default. Maybe we want to change default to /sat/sensor ?
        #self.FName['base_dirs'] = [os.getenv('SATDATROOT') + '/meghatropiques/saphir']
        # outer is 1100km
        self.swath_width_km = 1700
        self.mins_per_file = 120
        self.pathnameformat = ''
        #self.data_types = {}


class SEVIRISensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        # ME10_1380430_M0.tdfx
        #print 'SEVIRISensorInfo'
        OrigFName = self.OrigFName.copy()
        OrigFName2 = self.OrigFName.copy()
        OrigFName3 = self.OrigFName.copy()
        OrigFName['cls'] = 'SeviriTDFFileName'
        OrigFName['nameformat'] = '<satname>_<date{%j%H%M}>_<sat>'
        OrigFName['fieldsep'] = '_'
        OrigFName['fillvalue'] = 'x'
        OrigFName2['cls'] = 'FNMOCBFTGSFileName'
        OrigFName2['nameformat'] = '<satname>_<date{%j%H%M}>_<producttype>'
        OrigFName2['fieldsep'] = '_'
        OrigFName2['fillvalue'] = 'x'
        OrigFName3['cls'] = 'SeviriHRITFileName'
        # H-000-MSG1__-MSG1_IODC___-WV_073___-000005___-201612201830-C_
        OrigFName3['nameformat'] = '<resolution>-<always000>-<satname>-<alwaysmsg1iodc>-<channel>-<slice>-<date{%Y%m%d%H%M}>-<compression>'
        OrigFName3['noextension'] = True
        OrigFName3['fieldsep'] = '-'
        OrigFName3['fillvalue'] = 'x'
        OrigFName3['base_dir'] = os.path.join(gpaths['GEOIPS_OUTDIRS'],
                                          'data', 'incoming')
        OrigFName3['prefix_search_string'] = 'H-000-MSG'
        self.OrigFNames = [OrigFName3, OrigFName, OrigFName2]
        # Don't think legacy path is used anymore, can't run tdfs, and not downloading them.
        #self.FName['base_dirs'] = [os.getenv('SATDATROOT') + '/msg/hires']
        # Go with the default, which is actually SATDATROOT/sensor
        #self.FName['base_dirs'] = [os.getenv('SATDATROOT')]
        # outer is 1100km
        #self.swath_width_km = 900
        self.mins_per_file = 15
        self.interpolation_radius_of_influence = 4000
        self.FName['runfulldir'] = True
        self.swath_width_km = 12000
        # Don't think legacy path is used anymore, can't run tdfs, and not downloading them.
        #self.pathnameformat = ''
        opsep = os.path.sep
        self.pathnameformat = opsep.join(
                ['<satname>','<dataprovider>-<ext>',
                 '<date{%Y%m%d}>','<time{%H%M%S}>'])

        #self.data_types = {}

class SMAPSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        # SMAP_winds_RSS_20190124
        self.OrigFName['cls'] = 'SMAPFileName'
        self.OrigFName['nameformat'] = '<satname>_<stuff1>_<stuff2>_<data{%Y%m%d}>'
        self.OrigFName['fieldsep'] = '_'
        self.OrigFName['fillvalue'] = 'x'
        # outer is 1100km
        self.swath_width_km = 1000         #the real number is?
        self.pathnameformat = ''
        self.interpolation_radius_of_influence = 25000
        #self.data_types = {}

class SMOSSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        # RS_S2B00563.20143021221
        #self.OrigFName['cls'] = 'RSCATFileName'
        #self.OrigFName['nameformat'] = 'datatype_YYYYJJJHHMN'
        #self.OrigFName['fieldsep'] = '_'
        #self.OrigFName['fillvalue'] = 'x'
        # outer is 1100km
        #self.swath_width_km = 900
        self.pathnameformat = ''
        #self.data_types = {}


class SSMISensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        # RS_S2B00563.20143021221
        #self.OrigFName['cls'] = 'RSCATFileName'
        #self.OrigFName['nameformat'] = 'datatype_YYYYJJJHHMN'
        #self.OrigFName['fieldsep'] = '_'
        #self.OrigFName['fillvalue'] = 'x'
        self.interpolation_radius_of_influence = 5000
        self.swath_width_km = 1700 # 17000 in AWS? I think mistake
        self.mins_per_file = 30
        # Go with default now, no longer need to conform to old directory structure
        #self.FName['base_dirs'] = [os.getenv('SATDATROOT') + '/ssmi/global']
        self.pathnameformat = ''
        #self.data_types = {}


class SSMISSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        # US058SORB-RAWspp.sdris_f16_d20170907_s071200_e085800_r71661_cfnoc.raw
        # US058SORB-RAWspp.sdris_f17_d20170907_s011800_e012200_r55937_mMHSC_cfnoc.raw
        # 
        OrigFName = self.OrigFName.copy()
        OrigFName2 = self.OrigFName.copy()
        OrigFName['cls'] = 'SSMISRawFileName'
        OrigFName['nameformat'] = '<stuff1>_<satname>_<date{d%Y%m%d}>_<time{s%H%M%S}>_<endtime>_<revnum>_<dataprovider>'
        OrigFName['fieldsep'] = '_'
        OrigFName['fillvalue'] = 'x'
        OrigFName['noextension'] = False
        OrigFName2['cls'] = 'SSMISRawFileName'
        OrigFName2['nameformat'] = '<stuff1>_<satname>_<date{d%Y%m%d}>_<time{s%H%M%S}>_<endtime>_<revnum>_<stuff3>_<dataprovider>'
        OrigFName2['fieldsep'] = '_'
        OrigFName2['fillvalue'] = 'x'
        OrigFName2['noextension'] = False
        self.OrigFNames = [OrigFName, OrigFName2]
        self.pathnameformat = '<date{%Y%m%d.%H}>'
        self.swath_width_km = 1700
        self.mins_per_file = 30
        self.interpolation_radius_of_influence = 15000
        #self.data_types = {}

class SourceStitchedSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        self.swath_width_km = 12000
        self.interpolation_radius_of_influence = 10000
        self.mins_per_file = 10



class TMISensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # MOD021KM.P2014290.0415.hdf
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        #self.OrigFName['cls'] = 'TMIFileName'
        #self.OrigFName['nameformat'] = 'datatype.SYYYYJJJ.HHMN'
        #self.OrigFName['fieldsep'] = '.'
        #self.OrigFName['fillvalue'] = 'x'
        self.swath_width_km = 878
        #self.num_lines = 2030
        #self.num_samples = 1354
        self.mins_per_file = 95
        # Go with default now, no longer need to conform to old directory structure
        #self.FName['base_dirs'] = [os.getenv('SATDATROOT') + '/trmm']
        self.pathnameformat = '<data_type>'


class TPWSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        ''' Specify which filename format in datafilename
        this sensor uses.
        NPR.AAOP.NN.D13344.S1426.E1614.B4409596.NS
        NPR.MHOP.M1.D13344.S1703.E1758.B0637980.NS
        3rd field: NK NOAA-15
                    NL NOAA-16
                    NM NOAA-17
                    NN NOAA-18
                    NP NOAA-19
                    M2 METOP-2/A
        2nd field:  AAOP: AMSU-A
                    ABOP: AMSU-B
                    MHOP: AMSU-B
        '''
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        self.OrigFName['cls'] = 'TPWHE4FileName'
        self.OrigFName['nameformat'] = '<npr>.<comp>.<tpw>.<date{S%y%j%H%M}>.<enddate>.<endtime>'
        self.OrigFName['fieldsep'] = '.'
        self.OrigFName['fillvalue'] = 'x'
        OrigFName2 = self.OrigFName.copy()
        OrigFName2['cls'] = 'TPWHE4FileName'
        OrigFName2['nameformat'] = '<npr>.<comp>.<tpw>.<date{S%y%j%H%M}>.<enddate>.<endtime>.<he4>'
        OrigFName2['fieldsep'] = '.'
        OrigFName2['fillvalue'] = 'x'
        self.OrigFNames = [self.OrigFName, OrigFName2]
        # MLS this was screwing up pass predictor - checks if self.geostationary is True, if so
        # tries to predict coverage. Think about how to handle this... Don't think this would break
        # anything else...
        #self.geostationary = True
        self.interpolation_radius_of_influence = 20000
        #self.swath_width_km = 2200
        #self.num_lines = 2030
        #self.num_samples = 1354
        #self.mins_per_file = 5
        #self.FName['base_dirs'] = [os.getenv('SATDATROOT') + '/amsua/global']
        #self.pathnameformat = '<date{%Y%m%d}>'


class TPWMIMICSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        ''' Specify which filename format in datafilename
        this sensor uses.
        '''
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        self.OrigFName['cls'] = 'TPWMIMICFileName'
        self.OrigFName['nameformat'] = '<date{comp%Y%m%d}>.<time{%H%M%S}>'
        self.OrigFName['fieldsep'] = '.'
        self.OrigFName['fillvalue'] = 'x'
        self.OrigFNames = [self.OrigFName]
        if os.getenv('PROJECTS'):
            self.FName['base_dirs'] = [os.getenv('PROJECTS') + '/arunas/MIMIC']
        # MLS this was screwing up pass predictor - checks if self.geostationary is True, if so
        # tries to predict coverage. Think about how to handle this... Don't think this would
        # break anything else.
        #self.geostationary = True
        self.interpolation_radius_of_influence = 200000


class VIIRSSensorInfo(SensorInfo):

#    def __new__(cls, satellite = None):
#        print cls
#        obj = super(SensorInfo, cls).__new__(cls)
#        return obj


    def _set_sensor_atts(self):
        #print 'In viirs self._set_sensor_atts'
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        #
        #  Changed OrigFName3 nameformat to new SIPS filename format
        #  VNP02IMG.A2017332.1548.001.2017332192239.uwssec.nc
        #  20171129  Kim
        OrigFName1 = self.OrigFName.copy()
        OrigFName2 = self.OrigFName.copy()
        OrigFName3 = self.OrigFName.copy()

        OrigFName1['cls'] = 'NPPFileName'
        OrigFName1['nameformat'] = '<datatype>_<satname>_<date{d%Y%m%d}>_<time{t%H%M%S%f}>_<endtime>_<orbitnum>_<creationtime>_<dataoriginator>_<datalevel>'
        OrigFName1['fieldsep'] = '_'
        OrigFName1['fillvalue'] = 'x'
        OrigFName1['noextension'] = False

        OrigFName2['cls'] = 'NPPFileName'
        OrigFName2['nameformat'] = '<datatype>_<satname>_<date{d%Y%m%d}>_<time{t%H%M%S%f}>_<endtime>_<orbitnum>_<creationtime>_<dataoriginator>_<datalevel>'
        OrigFName2['fieldsep'] = '_'
        OrigFName2['fillvalue'] = 'x'
        OrigFName2['noextension'] = False
        if os.getenv('FROMBERYLDIR'):
            OrigFName2['base_dir'] = os.getenv('FROMBERYLDIR')
        else:
            OrigFName2['base_dir'] = gpaths['GEOIPS_OUTDIRS'] + '/npp/viirs'

        OrigFName2['cls'] = 'NPPFileName'
        OrigFName2['nameformat'] = '<date{%Y%m%d}>.<time{%H%M%S}>.<satname>.<sensorname>.<dataoriginator_datalevel>.<x1>.<datatype>.<x2>.<endorbitcreationtime>'
        OrigFName2['fieldsep'] = '.'
        OrigFName2['fillvalue'] = 'x'
        OrigFName2['noextension'] = False
        if os.getenv('FROMBERYLDIR'):
            OrigFName2['base_dir'] = os.getenv('FROMBERYLDIR')
        else:
            OrigFName2['base_dir'] = gpaths['GEOIPS_OUTDIRS'] + '/npp/viirs'

        OrigFName3['cls'] = 'NPPFileName'
        OrigFName3['nameformat'] = '<datatype>.<date{A%Y%j}>.<time{%H%M}>.<datalevel>.<creationtime>.<dataoriginator>'
        OrigFName3['fieldsep'] = '.'
        OrigFName3['fillvalue'] = 'x'
        OrigFName3['noextension'] = False

        self.FName['runfulldir'] = True
        self.FName['default_producttype'] = 'sdr'
        self.OrigFName = OrigFName1
        self.OrigFNames = [OrigFName1, OrigFName2, OrigFName3]

        # datatypee is sdr for legacy viirs tdfs from beryl/old GeoIPS
        legacy_oldgeoips_sdr = ['sdr']

        imgtc_geo = ['GITCO']
        #img_geo = ['GIMGO']
        img_data = ['SVI%02d' % (num + 1) for num in range(5)]

        modtc_geo = ['GMTCO']
        #mod_geo = ['GMODO']
        mod_data =  ['SVM%02d' % (num + 1) for num in range(16)]

        dnb_geo = ['GDNBO']
        dnb_data = ['SVDNB']

        ncc_geo = ['GNCCO']
        ncc_data = ['VNCCO']

        cloud_geo = ['GMODO']
        cloud_data = ['IICMO']

        rdr_data = ['RNSCA-RVIRS']

        self.geofiles = {
                    'GMTCO' : mod_data,
                    'GITCO' : img_data,
                    'GNCCO' : ncc_data,
                    'GMODO' : cloud_data,
                    'GDNBO' : dnb_data,
                    }

        self.prefixes = {}
        self.prefixes = {
                     'sdr': legacy_oldgeoips_sdr + img_data + mod_data + dnb_data + imgtc_geo + modtc_geo + dnb_geo,
                     'ncc': ncc_data + ncc_geo,
                     'cloud': cloud_data + cloud_geo,
                     'rdr': rdr_data
                    }

        self.all_prefixes = []

        for filetype in self.prefixes:
            self.all_prefixes += self.prefixes[filetype]

        self.all_prefixes = set(self.all_prefixes)

        self.swath_width_km = 3000
        # SIPS is 6 minutes, beryl is 85 seconds
        self.mins_per_file = 6
        self.num_lines = 1536
        self.num_samples = 6400
        # Slowly increasing this until the lines between granules go away.  Started at 1500, then 2000, 2500
        # This is used in scifile/containers.py register. Has to match biggest possible
        # pixel size (at edge of scan)
        # THIS IS SET IN READER NOW.  self.scifile.metadata['interpolation_radius_of_influence']
        self.interpolation_radius_of_influence = 10000 # 4500 - may need to think about this, AOT different than SDRs
        if os.getenv('OpsNPPDATA'):
            self.FName['base_dirs'] = [os.getenv('NPPDATA'), os.getenv('OpsNPPDATA')]
        elif os.getenv('NPPDATA'):
            self.FName['base_dirs'] = [os.getenv('NPPDATA')]
        self.pathnameformat='<satname>/<sensorname>/<dataprovider>/<producttype>-<ext>/<date{%Y%m%d}>/<time{%H%M%S}>-<timestamp>-<pid>'
        self.data_types = {}


class WINDSATSensorInfo(SensorInfo):
    def _set_sensor_atts(self):
        # This must match appropriate DataFileName class name in utils/path/datafilename.py
        # RS_S2B00563.20143021221
        #self.OrigFName['cls'] = 'RSCATFileName'
        #self.OrigFName['nameformat'] = 'datatype_YYYYJJJHHMN'
        #self.OrigFName['fieldsep'] = '_'
        #self.OrigFName['fillvalue'] = 'x'
        # outer is 1100km
        self.mins_per_file = 100
        self.swath_width_km = 1000
        self.data_types = {}
        self.pathnameformat = '<resolution>'


SensorInfo_classes = {
        # Needed to allow for stitched directory
        'sourcestitched':  SourceStitchedSensorInfo,
        'abi':  ABISensorInfo,
        'ahi':  AHISensorInfo,
        'amsr2':  AMSR2SensorInfo,
        'amsre':  AMSRESensorInfo,
        'amsua':  AMSUASensorInfo,
        'amsub':  AMSUBSensorInfo,
        'ascat':  ASCATSensorInfo,
        'atms':  ATMSSensorInfo,
        'clavrx-abi':  CLAVRXSensorInfo,
        'clavrx-ahi':  CLAVRXSensorInfo,
        'ccbg-abi':  CCBGSensorInfo,
        'ccbg-ahi':  CCBGSensorInfo,
        'modis': MODISSensorInfo,
        'gmi':  GMISensorInfo,
        'glm':  GLMSensorInfo,
        'gprof':  GPROFSensorInfo,
        'rscat':  RSCATSensorInfo,
        'oscat':  OSCATSensorInfo,
        # MLS 20160504 This might break legacy code, but it makes things difficult for having a
        # common sensorname.  Possibly need to make a "default" sensorname, and
        # allow for alternatives ? For now, just force it to gvar
        'gvar': GOESImagerSensorInfo,
        #'goes': GOESImagerSensorInfo,
        #'gvissr':  GOESImagerSensorInfo,
        'jami':  JAMISensorInfo,
        'mint':  MINTSensorInfo,
        'smos':  SMOSSensorInfo,
        'windsat':  WINDSATSensorInfo,
        'saphir': SAPHIRSensorInfo,
        'smap-spd':  SMAPSensorInfo,
        'ssmi':  SSMISensorInfo,
        'ssmis':  SSMISSensorInfo,
        'ols':  OLSSensorInfo,
        'navgemforecast': NAVGEMForecastSensorInfo,
        'navgem': MODELSensorInfo,
        'coamps': MODELSensorInfo,
        'icap': ICAPSensorInfo,
        'winds': WINDSSensorInfo,
        'naapsaot': NAAPSAOTSensorInfo,
        'seviri':  SEVIRISensorInfo,
        'tmi':  TMISensorInfo,
        'tpw_cira': TPWSensorInfo,
        'tpw_mimic': TPWMIMICSensorInfo,
        'viirs': VIIRSSensorInfo,
        }


SatInfo_classes = {
        # Needed to allow for stitched directory
        'sourcestitched':  SourceStitchedSatInfo,
        'npp': NPPSatInfo,
        'jpss': N20SatInfo,
        'aqua': AQUASatInfo,
        'coriolis': CORIOLISSatInfo,
        'f08': F08SatInfo,
        'f10': F10SatInfo,
        'f11': F11SatInfo,
        'f13': F13SatInfo,
        'f14': F14SatInfo,
        'f15': F15SatInfo,
        'f16': F16SatInfo,
        'f17': F17SatInfo,
        'f18': F18SatInfo,
        'f19': F19SatInfo,
        'gcom-w1': GCOMSatInfo,
        'goesE': GOESESatInfo,
        'goes16': GOES16SatInfo,
        'G16': GOES16SatInfo,
        'goes17': GOES17SatInfo,
        'G17': GOES17SatInfo,
        'goesW': GOESWSatInfo,
        'gpm': GPMSatInfo,
        # Note I changed reader to use h8 explicitly rather than himawari-8
        #   pulled from the datafile. We should set our own internal satellite
        #   names - delimiters can mess up our path format delimiters.
        # Make an executive decision now that all platform names and sensor names
        #   should contain ONLY alphanumeric characters.
        'himawari8': HIMAWARI8SatInfo,
        'iss': ISSSatInfo,
        'model': MODELSatInfo,
        'mt2': MT2SatInfo,
        'mt1': MT1SatInfo,
        'nrljc': NRLJCSatInfo,
        'proteus': PROTEUSSatInfo,
        'meteoIO': ME8SatInfo,
        # THIS MUST BE CHANGED IF SATELLITE CHANGES. Everything else can be generalized
        'meteoEU': ME11SatInfo,
        'me10': ME10SatInfo,
        'me11': ME11SatInfo,
        'me9': ME9SatInfo,
        'me7': METEO7SatInfo,
        'msg1': ME8SatInfo,
        'msg2': ME9SatInfo,
        'msg3': ME10SatInfo,
        'msg4': ME11SatInfo,
        'meghatropiques': MEGHATROPIQUESSatInfo,
        'oceansat-2': OCEANSATSatInfo,
        'scatsat-1': SCATSAT1SatInfo,
        'metopa': METOPASatInfo,
        'metopb': METOPBSatInfo,
        'n19': N19SatInfo,
        'n18': N18SatInfo,
        'n16': N16SatInfo,
        'n15': N15SatInfo,
        'm2a': M2ASatInfo,
        'multi': MULTISatInfo,
        'navgem': NAVGEMSatInfo,
        'smap': SMAPSatInfo,
        'windvectors': WindVectorsSatInfo,
        'terra': TERRASatInfo,
        'trmm': TRMMSatInfo,
        }


def all_sats_for_sensor(sensor):
    '''
    Return the satellites that carry the input sensor as a list of strings.

    +-----------+------+----------------------+
    | Parameter | Type | Description          |
    +===========+======+======================+
    | sensor    | str  | The name of a sensor |
    +-----------+------+----------------------+
    '''
    sats = []
    for sat in SatInfo_classes.keys():
        if sensor in SatInfo_classes[sat]().sensornames:
            sats.append(sat)
    return sats


def open_satinfo(satellite):
    '''
    Returns a SatInfo instance for the input satellite name.
    +-----------+------+-------------------------+
    | Parameter | Type | Description             |
    +===========+======+=========================+
    | satellite | str  | The name of a satellite |
    +-----------+------+-------------------------+
    '''
    return SatInfo_classes[satellite]()


def all_sensors_for_sat(sat):
    '''
    Returns a the sensors available on the given satellite as a list of strings.

    +-----------+------+-------------------------+
    | Parameter | Type | Description             |
    +===========+======+=========================+
    | sat       | str  | The name of a satellite |
    +-----------+------+-------------------------+
    '''

    sensors = []
    for sensor in SatInfo_classes[sat]().sensornames:
        sensors.append(sensor)

    return sensors


def all_available_sensors():
    '''
    Returns a list of all known sensors.
    '''

    sensors = set()
    for sat in SatInfo_classes.keys():
        for sensor in SatInfo_classes[sat]().sensornames:
            if sensor not in SensorInfo_classes.keys():
                log.debug('WARNING Sensor \''+sensor+'\' listed in SatInfo for \''+
                      sat + '\' but not listed in SensorInfo_classes! Add SensorInfo class for \'' + sensor + '\'')
            else:
                sensors.add(sensor)
    return sorted(list(sensors))


def all_available_satellites():
    '''
    Returns a list of all known satellites.
    '''
    sats = []
    for sat in SatInfo_classes.keys():
        sats.append(sat)

    return sorted(sats)


def get_celestrak_tle_name(satellite):
    '''
    Returns the name used in CelesTrak Two Line Elements for the given satellite.

    +-----------+------+-------------------------+
    | Parameter | Type | Description             |
    +===========+======+=========================+
    | satellite | str  | The name of a satellite |
    +-----------+------+-------------------------+
    '''
    return SatInfo_classes[satellite]().celestrak_tle_name


def get_old_celestrak_tle_names(satellite):
    '''
    Returns any old names used in CelesTrak Two Line Elements for the given satellite.

    +-----------+------+-------------------------+
    | Parameter | Type | Description             |
    +===========+======+=========================+
    | satellite | str  | The name of a satellite |
    +-----------+------+-------------------------+
    '''
    return SatInfo_classes[satellite]().old_celestrak_tle_names


def get_tscan_tle_name(satellite):
    '''
    Returns the name used in TeraScan Two Line Elements for the given satellite.
    '''
    return SatInfo_classes[satellite]().tscan_tle_name
