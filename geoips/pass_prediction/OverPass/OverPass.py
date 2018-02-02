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

# Python Standard Libraries
import os
import urllib2
from httplib import BadStatusLine
import re
import logging
from datetime import datetime,timedelta
import socket


# GeoIPS Libraries
from geoips.utils.cmdargs import CMDArgs
from geoips.utils.log_setup import interactive_log_setup
from geoips.utils.path.filename import _FileNameBase

log = interactive_log_setup(logging.getLogger(__name__))

class OverPass(object):
    def __init__(self,
                satellite_name,
                startdt,
                enddt,
                sectornames,
                cpa = 0,
                noprocess = False,
                force_qsub = False,
                lunar_phase=None,
                lunar_alt=None,
                solar_alt=None,
                clat=None,
                clon=None,
               ):
        self.startdt = startdt
        self.enddt = enddt
        self.total_time = enddt-startdt
        self.satellite_name = satellite_name
        self.sectornames = sectornames
        self.noprocess = noprocess
        self.cpa = float(cpa)
        self.actualsectornames = set()
        self.clat = clat
        self.clon = clon
        for sect in self.sectornames:
            self.actualsectornames.add(re.sub('[0-9]{6}$','',sect))
        self.total_mins = (self.total_time.seconds / 60.0) + self.total_time.days*24*60
        self.lunar_phase = lunar_phase
        self.lunar_alt = lunar_alt
        self.solar_alt = solar_alt
        LSstuff= ''
        LLstuff = ''
        if self.lunar_phase:
            LSstuff += ' {0:5.1f}LP'.format(lunar_phase*100)
        if self.lunar_alt:
            LSstuff += ' {0:5.1f}LA'.format(lunar_alt)
        if self.solar_alt:
            LSstuff += ' {0:5.1f}SA'.format(solar_alt)
        if self.clat:
            LLstuff += ' {0:5.1f}CLat'.format(self.clat)
        if self.clon:
            LLstuff += ' {0:5.1f}CLon'.format(self.clon)
        self.opass = self.basedt.strftime('%Y/%m/%d %H:%M:%S '+self.satellite_name+' {0:5.0f} '.format(self.cpa)+'-'.join(self.sectornames)+' {0:5.1f} '.format(self.total_mins)+LSstuff+LLstuff)
        self.tcpass = self.basedt.strftime('%Y/%m/%d %H:%M:%S '+self.satellite_name.upper()+' '+str(int(self.cpa)))
        self.bigindent = '\n                                                  '

    def __str__(self):
        return self.opass

    @property
    def basedt(self):
        self._basedt = self.startdt + (self.enddt - self.startdt) / 2
        return self._basedt

    @staticmethod
    def fromfocuspasses(opass, noprocess=False):
        opass = opass.strip()

        parts = opass.split()
        satellite_name = parts[2].lower()
        try:
            sectornames = parts[4].split('-')
        except:
            sectornames = "unknown"
        try:
            total_time = timedelta(minutes=float(parts[5]))
        except:
            log.warning('Total minutes not specified for overpass, defaulting to 10')
            total_time = timedelta(minutes=10.0)
        parts = opass.strip().split()
        basedt = datetime.strptime(parts[0]+parts[1], '%Y/%m/%d%H:%M:%S')
        startdt = basedt - total_time/2 - timedelta(minutes=1.0)
        enddt = basedt + total_time/2 + timedelta(minutes=1.0)
        cpa = parts[3]
        log.debug('                startdt: '+str(startdt)+' basedt: '+str(basedt)+' enddt: '+str(enddt)+' total_time: '+str(total_time))
        try:
            lunar_phase = float(parts[6].replace('LP',''))
        except:
            lunar_phase=None
        try:
            lunar_alt = float(parts[7].replace('LA',''))
        except:
            lunar_alt = None
        try:
            solar_alt = float(parts[8].replace('SA',''))
        except:
            solar_alt = None
        return OverPass(satellite_name,startdt,enddt,sectornames, cpa=cpa,noprocess=noprocess,lunar_phase=lunar_phase,lunar_alt=lunar_alt,solar_alt=solar_alt)

    def overlap(self,other,maxtimediff,other_startdt=None,other_enddt=None):
        if other_startdt == None or other_enddt == None:
            log.info('RUNNING OverPass is_concurrent_with')
            retval = _FileNameBase.is_concurrent_with(self.startdt,
                                        other.startdt,
                                        self.enddt,
                                        other.enddt,
                                        maxtimediff)
            log.info('DONE RUNNING OverPass is_concurrent_with')
            return retval
        else:
            log.debug('self start: '+str(self.startdt))
            log.debug('self end: '+str(self.enddt))
            log.debug('other start: '+str(other_startdt))
            log.debug('other end: '+str(other_enddt))
            log.info('RUNNING OverPass is_concurrent_with')
            retval = _FileNameBase.is_concurrent_with(self.startdt,
                                        other_startdt,
                                        self.enddt,
                                        other_enddt,
                                        maxtimediff)
            log.info('DONE RUNNING OverPass is_concurrent_with')
            return retval

    def combine(self,other,cutofflength=20,individual=False):
        if other == None:
            return self
        log.debug('total time: '+str(other.total_time))
        log.debug(str(cutofflength)+' mins: '+str(timedelta(minutes=cutofflength)))
        if other.total_time < timedelta(minutes=cutofflength):
            log.debug('cutt off after '+str(cutofflength)+' minutes,still ok')
        else:
            log.debug('shouldnt do any more')
        #if self.satellite_name == other.satellite_name and self.overlap(other,timedelta(minutes=5)) == True:
        if self.satellite_name == other.satellite_name and \
                other.total_time < timedelta(minutes=cutofflength) and \
                self.overlap(other,timedelta(minutes=5)) == True:
            #print '    individual: '+str(individual)+' self.sectornames: '+str(self.sectornames)+' other.sectornames: '+str(other.sectornames)
            if individual and self.sectornames != other.sectornames:
                #print 'self:  '+self.opass+' '+str(self.startdt)+' '+str(self.enddt)
                #print 'other: '+other.opass+' '+str(other.startdt)+' '+str(other.enddt)
                #print '  returning separately'
                return [self,other]
            if self.startdt < other.startdt:
                startdt = self.startdt
            else:
                startdt = other.startdt
            if self.enddt > other.enddt:
                enddt = self.enddt
            else: 
                enddt = other.enddt
            #print 'self:  '+self.opass+' '+str(self.startdt)+' '+str(self.enddt)
            #print 'other: '+other.opass+' '+str(other.startdt)+' '+str(other.enddt)
            #print '  combining: '+str(startdt)+' to '+str(enddt)
            sectornames = set(self.sectornames)
            sectornames.update(set(other.sectornames))
            sectornames = sorted(list(sectornames))
            new_cpa = (float(self.cpa) + float(other.cpa) ) / 2.0
            return OverPass(self.satellite_name,startdt,enddt,sectornames,cpa=new_cpa)
        else:
            #print 'self:  '+self.opass+' '+str(self.startdt)+' '+str(self.enddt)
            #print 'other: '+other.opass+' '+str(other.startdt)+' '+str(other.enddt)
            #print '  returning separately'
            return [self,other]

