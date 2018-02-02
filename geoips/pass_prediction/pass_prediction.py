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

# Standard Python Libraries
import os
import argparse
import logging
import commands
import operator
from datetime import datetime, timedelta
import math
import pickle

# Installed Libraries
import ephem
import pyresample
from IPython import embed as shell

# GeoIPS Libraries
from .OverPass.OverPass import OverPass
import geoips.sectorfile as sectorfile
from geoips.utils.path.filename import _FileNameBase
from geoips.utils.log_setup import interactive_log_setup,root_log_setup
from geoips.utils.satellite_info import SatSensorInfo,all_sensors_for_sat,get_celestrak_tle_name,get_old_celestrak_tle_names,SatInfoError,open_satinfo
from geoips.utils.email_errors import email_error
from geoips.utils.plugin_paths import paths as gpaths

log = interactive_log_setup(logging.getLogger('__name__'))


bigindent='\n'+' '*40

def open_predictor(predictor,sat,dt):

    nn = 0
    op = None
    tle = None
    emailed_level1 = False
    emailed_level2 = False
    while not tle and nn < 90:
        currdt = dt-timedelta(days=nn)
        #log.info(str(currdt)+' '+str(dt)+' '+str(nn))
        nn += 1 
        # Don't email for missing TLEs if the satellite is dead...
        if open_satinfo(sat).satellite_dead:
            continue
        if nn > 4 and dt < datetime.utcnow():
            errmsg = 'Haven\'t seen a TLE from '+sat+' in more than '+str(nn)+' days, grep '+str(get_celestrak_tle_name(sat))+' $SATOPS/longterm_files/tle/'+currdt.strftime('%Y/%m/*')+'; grep '+str(get_celestrak_tle_name(sat))+' $SATOPS/longterm_files/tle/*.txt'
            subject = 'CHECK ON '+os.getenv('USER')+' '+str(gpaths['BOXNAME'])+' '+sat+' TLE !!!'

        if nn > 8 and dt < datetime.utcnow():
            #Only use TLE for 3 months in future, force people to find TLEs if missing in past
            # rather than just using out of date ones
            # Email Level 2 Support Team
            if not emailed_level2:
                emailed_level2 = True
                email_error(errmsg,subject,errorlevel=2)
            continue
        elif nn > 6 and dt < datetime.utcnow():
            # If we haven't seen the TLE for 6 days, email the level 2 support team
            if not emailed_level2:
                emailed_level2 = True
                email_error(errmsg,subject,errorlevel=2)
        elif nn > 4 and dt < datetime.utcnow():
            # If we haven't seen the TLE for 4 days, email Kim, and Mindy
            if not emailed_level1:
                emailed_level1 = True
                email_error(errmsg,subject,errorlevel=1)

        tlepath = gpaths['SATOPS']+'/longterm_files/tle/'+currdt.strftime('%Y/%m/%d')
        try:
            log.info('    Trying tlepath: '+tlepath+' TLE names: '+str(get_celestrak_tle_name(sat))+' '+str(get_old_celestrak_tle_names(sat)))
            tlefile = open(tlepath,'r')
        except IOError,resp:
            log.warning(str(resp)+' could not open tlepath: '+tlepath+': try previous day')
            continue
        except AttributeError,resp:
            log.warning(str(resp)+': try previous day')
            continue

        for line in tlefile:
            #print 'line: '+str(line).lower()+' sat: '+str(sat).lower()
            #if tle_names[sat].lower() in line.lower():
            for tlename in [get_celestrak_tle_name(sat)]+get_old_celestrak_tle_names(sat):
                if not tle and tlename and  tlename.lower() in line.lower():
                    line1 = next(tlefile)
                    line2 = next(tlefile)
                    #log.info(sat+line1+line2)
                    #tle = ephem.readtle(tle_names[sat],line1,line2)
                    tle = ephem.readtle(tlename,line1,line2)

    if not tle:
        log.warning('Never found TLE, satellite_dead: '+str(open_satinfo(sat).satellite_dead))
        log.interactive('Never found TLE, satellite_dead: '+str(open_satinfo(sat).satellite_dead))
    
    return op,tle


def get_overpasses(predictor,
        sat,
        sect,
        sensor_info,
        sector_width_km,
        start_datetime,
        end_datetime,
        num_hours,
        lat,
        swath_lons,
        swath_lats,
        clon_deg,
        mins_per_file,
        est_time,
        dynamic_datetime,
        passes = [],
        tle=None,
        op=None):

    opasses = []
    #passes = []

    earth_radius_km = 6372.795
    #swath_width_km = sensor_info['swath_width_km']
    #orbit_period_min = sensor_info['orbit_period_min']
    swath_width_km = sensor_info.swath_width_km
    #orbit_period_min = sensor_info['orbit_period_min']
    orbital_period = sensor_info.orbital_period
    swath = 0
    for (currlon,currlat) in zip(swath_lons,swath_lats):
        swath = swath + 1
        #log.info(str(swath_width_km)+' '+str(sector_width_km))
        # Need to check more points for bigger sectors
        if swath_width_km and swath > 5 and float(swath_width_km * 4) > sector_width_km:
            continue
        if swath_width_km and swath > 3 and float(swath_width_km * 2) > sector_width_km:
            continue
        elif swath_width_km and swath > 1 and float(swath_width_km) > sector_width_km:
            log.info('            only running once, small sector')
            continue
        log.info('\n\n            Trying '+sat+' lon: '+str(currlon)+' lat: '+str(currlat)+' starting at '+start_datetime.strftime('%Y/%m/%d %H:%M:%S')+' for '+str(num_hours)+'h')

        if predictor == 'pyorbital':
            popasses = op.get_next_passes(start_datetime,num_hours,currlon,currlat,int(0))
            for opass in popasses:
                # Only checking mins_per_file extra at the beginning
                opass_middt = opass[2] - timedelta(minutes=(mins_per_file/2.0))
                opassstr = opass_middt.strftime('%Y/%m/%d %H:%M:%S')+' '+sat+' 0 '+sect.name+' '+str(est_time)
                opasses.append(OverPass.fromfocuspasses(opassstr))

        elif predictor == 'pyephem':
            sector = ephem.Observer()
            sector.lon = str(currlon)
            sector.lat = str(currlat)
            sector.date = start_datetime.strftime('%Y/%m/%d %H:%M:%S')
            sector.elevation = 0.0
            #print sector
            #print tle
            moon = ephem.Moon()
            sun = ephem.Sun()
            try:
                opass = sector.next_pass(tle)
            except ValueError:
                opass = None
            while (sensor_info.geostationary or ( opass and opass[2])) and (sector.date.datetime() - start_datetime) < timedelta(hours=num_hours):
                moon.compute(sector)
                sun.compute(sector)
                #print 'MOON PHASE '+str(moon.moon_phase)
                #print 'SUN ALT: '+str(sun.alt * (180/math.pi))
                #print 'MOON ALT: '+str(moon.alt * (180/math.pi))
                #shell()
                if sensor_info.geostationary:
                    tle.compute(sector)
                else:
                    tle.compute(opass[2].datetime())
                ptsatdeg = pyresample.spherical_geometry.Coordinate(lon=math.degrees(tle.sublong),lat=math.degrees(tle.sublat))
                ptsecdeg = pyresample.spherical_geometry.Coordinate(lon=math.degrees(sector.lon),lat=math.degrees(sector.lat))
                #log.info(ptsatdeg)
                #log.info(ptsecdeg)
                CPA_km = ptsatdeg.distance(ptsecdeg)*earth_radius_km
                if swath > 1:
                    # First swath is center lat/lon. Others are additional points to check 
                    # for big sectors. Use distance from center for display (but distance 
                    # from new point for checking if we have coverage...)
                    ptcsecdeg = pyresample.spherical_geometry.Coordinate(lon=clon_deg,lat=math.degrees(sector.lat))
                    CPA_fullkm = ptcsecdeg.distance(ptsatdeg)*earth_radius_km
                else:
                    ptcsecdeg = ptsecdeg
                    CPA_fullkm = CPA_km

                if not sensor_info.geostationary:
                    opdt = opass[2].datetime()
                else:
                    # OP datetime is CENTER time!!!!
                    opdt = start_datetime+timedelta(minutes=est_time / 2)

                #opassstr = opdt.strftime('%Y/%m/%d %H:%M:%S')+' '+sat+' '+str(CPA_fullkm)+' '+sect.name+' '+str(est_time)+' LP'+str(moon.moon_phase)+' LA'+str(moon.alt*(180/math.pi))+' SA'+str(sun.alt*(180/math.pi))
                curropass = OverPass(sat,
                                    startdt=opdt-timedelta(minutes=est_time/2),
                                    enddt=opdt+timedelta(minutes=est_time/2),
                                    sectornames=[sect.name],
                                    cpa=CPA_fullkm,
                                    lunar_phase=moon.moon_phase,
                                    lunar_alt=moon.alt*(180/math.pi),
                                    solar_alt=sun.alt*(180/math.pi),
                                    clat=math.degrees(sector.lat),
                                    clon=math.degrees(sector.lon),)
                # Change checking for pass predictor to include overpasses up to-
                # CPA_km rather than just 0.6*CPA_km. Was missing overpasses for global
                # products, which made the composite image get cut off at the missing-
                # overpass
                # Need to make sure we are not after end_datetime... Previously just checked using num_hours,
                # which is an approximation...
                #if CPA_km < swath_width_km and (opass[2].datetime() - timedelta(hours=num_hours)) < start_datetime and opass[2].datetime() < end_datetime:
                # MLS 20160523 NEED TO FIX THIS!  
                # I think we are defaulting to end_datetime = TIME OF DATA, which is not what we
                #   want at all for static sectors. end_datetime should actually be the end of the
                #   range we want to match for static sectors. For now put it back the way it was,
                #   because everything stopped, but we need to fix this.
                # MLS 20160525, I think I didn't actually uncomment this line on Monday... Try now.
                #   also, KNMI pass predictor for file merging was failing with the end_datetime check.
                if CPA_km < swath_width_km and (opdt - timedelta(hours=num_hours)) < start_datetime:
                    #opasses.append(OverPass.fromfocuspasses(opassstr))
                    #log.info('                USING '+str(swath_width_km)+' '+str(CPA_km)+' '+opassstr)
                    log.info('                USING '+str(swath_width_km)+' '+str(CPA_km)+' '+curropass.opass)
                    opasses.append(curropass)
                else:
                    #log.info('                SKIP  '+str(swath_width_km)+' '+str(CPA_km)+' '+opassstr)
                    log.info('                SKIP  '+str(swath_width_km)+' '+str(CPA_km)+' '+curropass.opass)
                #log.interactive('      '+str(ptsecdeg)+' '+str(ptcsecdeg)+' '+str(ptsatdeg))

                if sensor_info.geostationary:
                    break


                #sector.date = opass[2].datetime() + timedelta(minutes=.5*(orbit_period_min))
                sector.date = opass[2].datetime() + timedelta(seconds=.5*(orbital_period))
                old_opass = opass[2]
                try:
                    opass = sector.next_pass(tle)
                    # Was getting stuck in a loop for Arctic NIC sector coriolis... 
                    if opass[2] and old_opass and abs(opass[2].datetime() - old_opass.datetime()) < timedelta(minutes=5):
                        opass=None
                except ValueError:
                    opass = None

        for opass in opasses:
            overlap_existing = False
            for op in passes:
                if (op.satellite_name == opass.satellite_name) and (op.sectornames == opass.sectornames) and (_FileNameBase.is_concurrent_with(opass.basedt,op.basedt,maxtimediff=timedelta(minutes=10))):
                    #log.interactive('satname: '+op.satellite_name)
                    #log.interactive('names: '+str(op.sectornames)+' '+str(opass.sectornames))
                    #log.interactive('overlaps'+str(opass)+' '+str(op))
                    overlap_existing = True
            if not overlap_existing:
                    #log.interactive(opass.basedt-timedelta(hours=3))
                #if sect.isdynamic and sect.dynamic_endtime:
                #    log.info(sect.dynamic_datetime)
                #    log.info(sect.dynamic_endtime)
                #    if FileName.is_concurrent_with(opass.start_datetime,sect.dynamic_datetime,opass.end_datetime,sect.dynamic_endtime):
                #    #if not dynamic_datetime or FileName.is_concurrent_with(opass.basedt-timedelta(hours=3),dynamic_datetime,maxtimediff=timedelta(hours=3)):
                passes.append(opass)
    return passes

def time_range_defaults(start_datetime=None,
                        end_datetime=None,
                        num_hours_back_to_start=None,
                        num_hours_to_check=None):
    if num_hours_back_to_start != None or num_hours_to_check != None:
        if num_hours_to_check == None:
            num_hours_to_check = num_hours_back_to_start
            end_datetime = datetime.utcnow()
            start_datetime = end_datetime - timedelta(hours=int(num_hours_back_to_start))
        elif num_hours_back_to_start == None:
            num_hours_back_to_start = num_hours_to_check
            end_datetime = datetime.utcnow()
            start_datetime = end_datetime - timedelta(hours=int(num_hours_back_to_start))
        else:
            start_datetime = datetime.utcnow() - timedelta(hours=int(num_hours_back_to_start))
            end_datetime = start_datetime + timedelta(hours=int(num_hours_to_check))
        log.info('num_hours_back_to_start trumps, starting '+
                    str(num_hours_back_to_start)+'h ago, checking for '+
                    str(num_hours_to_check)+'h')
    elif start_datetime == None and end_datetime == None:
        end_datetime = datetime.utcnow() 
        start_datetime = end_datetime - timedelta(days=1)
    elif start_datetime == None:
        try: 
            end_datetime = datetime.strptime(end_datetime,'%Y%m%d.%H%M%S')
        except TypeError:
            pass
        start_datetime = end_datetime - timedelta(days=1)
    elif end_datetime == None:
        try: 
            start_datetime = datetime.strptime(start_datetime,'%Y%m%d.%H%M%S')
        except TypeError:
            pass
        end_datetime = start_datetime + timedelta(days=1)
        if (datetime.utcnow() < end_datetime):
            end_datetime = datetime.utcnow()
    else:
        try: 
            start_datetime = datetime.strptime(start_datetime,'%Y%m%d.%H%M%S')
        except TypeError:
            pass
        try: 
            end_datetime = datetime.strptime(end_datetime,'%Y%m%d.%H%M%S')
        except TypeError:
            pass
            
    log.info('Start time: '+str(start_datetime))
    log.info('End time:   '+str(end_datetime))
    return [start_datetime,end_datetime]


def is_concurrent_with(startdt,other_startdt,enddt,other_enddt):
    '''Check if 2 time ranges overlap in time. Takes 4 arguments - 
    startdt, other_startdt, enddt, other_enddt'''
    timediff1 = (abs(enddt - other_startdt))
    timediff2 = (abs(startdt - other_enddt))
    if timediff1 < timedelta(hours=0) or timediff2 < timedelta(hours=0): 
       return True
    if enddt < other_startdt or other_enddt < startdt:
       return False
    else:
       return True

def get_pass_prediction_list(satellites,get_start_dt,get_end_dt,single=False,cutofflengths=None,sectorlist=None):

    ind_opasses = None
    comb_opasses = None
    ret_opasses = {}

    # Check one day before current start dt, since we do pass prediction for more than a day
    day_count = (get_end_dt - get_start_dt).days + 4
    list_start_dt = get_start_dt - timedelta(1)

    log.info('get_start_dt: '+str(get_start_dt))
    log.info('get_end_dt: '+str(get_end_dt))

    staticdirname = os.getenv('PASS_PREDICTION_LIST_DIR')+'/static'
    dynamicdirname = os.getenv('PASS_PREDICTION_LIST_DIR')+'/dynamic'

    for dnt in [staticdirname,dynamicdirname]:
        fnames = []
        next_end_dt = None
        prev_fname = None
        prev_start_dt = None
        num_fnames= 0
        for n in range(day_count,-2,-1): 
            dt = list_start_dt+timedelta(n)

            dn = dnt+'/'+dt.strftime('%Y%m/%d')

            if not os.path.isdir(dn):
                log.debug('Directory does not exist, can not get pass_prediction_list: '+dn)
                continue

            log.info('Checking '+dn)

            files = os.listdir(dn)
            files.sort(key=lambda x: os.path.getmtime(dn+'/'+x))
            files.reverse()

            for fname in files:
                # Base everything off _individual file now...
                if '.pkl' not in fname and '_individual' in fname:
                    # skip most recent file in case it is being written...
                    # probably should handle this better, but should work for now...
                    #log.info('    checking file: '+fname)
                    start_dtstr,end_dtstr,rest = fname.split('_',2)
                    try:
                        start_dt = datetime.strptime(start_dtstr,'%Y%m%d.%H%M%S')
                        end_dt = datetime.strptime(end_dtstr,'%Y%m%d.%H%M%S')
                    except ValueError:
                        log.warning('SKIPPING: Invalid filename format '+fname+' '+commands.getoutput('ls --full-time '+dn+'/'+fname))
                        continue
                    if is_concurrent_with(get_start_dt,start_dt,get_end_dt,end_dt):
                        #log.info('start_dt: '+str(start_dt)+' end_dt: '+str(end_dt))
                        #log.info('next_end_dt: '+str(next_end_dt)+' prev_fname: '+str(prev_fname))
                        # Always skip the first file (in case it is being written to)
                        if num_fnames == 0:
                            num_fnames = num_fnames + 1
                            continue
                        num_fnames = num_fnames + 1
                        #Always take the most recent overlapping file (after skipping the first one)
                        log.debug(dn+'/'+fname+'.pkl '+str(start_dt)+' '+str(end_dt)+'\n')
                        if prev_fname == None:
                            log.debug(dn+'/'+fname+'.pkl '+str(start_dt)+' '+str(end_dt)+'\n')
                            fnames.append(dn+'/'+fname)
                            next_end_dt = start_dt
                        # Once we 
                        elif end_dt < next_end_dt:
                            log.debug(prev_fname+'.pkl '+str(start_dt)+' '+str(end_dt)+'\n')
                            fnames.append(prev_fname)
                            next_end_dt = prev_start_dt
                        prev_fname = dn+'/'+fname
                        prev_start_dt = start_dt

        for fname in fnames:
            # Base everything off _individual file now... Combined file recreated, so never even opened it anyway.
#            comb_fn = fname.replace('_individual','')+'.pkl'
            ind_fn = fname+'.pkl'

            log.info('Using pass prediction list '+ind_fn)
#            try: 
#                comb_opasses = pickle.load(open(comb_fn,'rb'))
#            except IOError:
#                log.info('No combined pass prediction list for this pass prediction run, cant open')
            try:
                ind_opasses = pickle.load(open(ind_fn,'rb'))
            except (IOError,EOFError):
                log.info('No individual pass prediction list for this pass prediction run, cant open')

#            if single == False:
#                for opass in comb_opasses:
#                    for sat in satellites:
#                        log.debug('opass.startdt: '+str(opass.startdt)+' opass.enddt: '+str(opass.enddt))
#                        log.debug('get_start_dt: '+str(get_start_dt)+' get_end_dt: '+str(get_end_dt))
#                        try:
#                            if opass.satellite_name == sat and get_start_dt.overlap(get_start_dt,opass.startdt,get_end_dt,opass.enddt):
#                                if opass not in ret_opasses:
#                                    log.debug('adding opass: '+str(opass))
#                                    ret_opasses.append(opass)
#                        except AttributeError,resp:
#                            if "'OverPass' object has no attribute 'satellite_name'" in resp:
#                                #log.error('Maintaining backwards compatibility with old pass prediction files: Not checking satellite name!')
#                                if get_start_dt.overlap(get_start_dt,opass.startdt,get_end_dt,opass.enddt):
#                                    if opass not in ret_opasses:
#                                        log.debug('adding opass: '+str(opass))
#                                        ret_opasses.append(opass)
                                
#            if single == True:
            for opass in ind_opasses:
                for sat in satellites:
                    log.debug('opass.startdt: '+str(opass.startdt)+' opass.enddt: '+str(opass.enddt))
                    log.debug('get_start_dt: '+str(get_start_dt)+' get_end_dt: '+str(get_end_dt))
                    try:
                        usesect = False
                        if sectorlist:
                            for sectname in opass.actualsectornames:
                                if 'tc' in sectname:
                                    log.debug('opass sectname: '+sectname.lower())
                                    log.debug('sectorlist: '+str(sectorlist))
                                if sectname.lower() in sectorlist:
                                    log.debug('usesect = True')
                                    usesect = True
                        else:
                            usesect = True
                        overlaps = is_concurrent_with(get_start_dt,opass.startdt,get_end_dt,opass.enddt)
                        satname = opass.satellite_name
                        #log.info('usesect: '+str(usesect)+' overlaps: '+str(overlaps)+' satname == sat '+str(satname == sat))
                        if satname == sat and usesect:
                            #log.info(opass)
                            if overlaps:
                                #log.info('checking '+str(opass)+' check start_dt: '+str(get_start_dt)+' check end_dt: '+str(get_end_dt))
                                if opass.opass not in ret_opasses:
                                    ret_opasses[opass.opass] = opass
                    except AttributeError,resp:
                        if "'OverPass' object has no attribute 'satellite_name'" in resp:
                            #log.error('Maintaining backwards compatibility with old pass prediction files: Not checking satellite name!')
                            if is_concurrent_with(get_start_dt,opass.startdt,get_end_dt,opass.enddt):
                                if opass not in ret_opasses:
                                    ret_opasses[opass.opass] = opass
    ret_opasses = ret_opasses.values()
    if single == False:
        ret_opasses = combine_overpasses(ret_opasses,cutofflengths)

    return ret_opasses

def pass_prediction(satellites, sensors, sector_file, sectorlist=None,start_datetime=None, end_datetime=None, no_fit=False, noprocess=False, both=False, single=False,force=False,sectorfiles=[],quiet=False):
    log.interactive('Running pass_prediction '+str(satellites)+' '+str(sensors)+' '+str(start_datetime)+' '+str(end_datetime))
    if quiet:
        log.setLevel(35)
    log.info('sectorfiles in pass_prediction: '+str(sectorfiles))


    if not sector_file:
        if sectorfiles:
            sector_file = sectorfile.open(sectorfiles=sectorfiles,
                            quiet=quiet)
        else:
            sector_file = sectorfile.open(allstatic=True, 
                            alldynamic=True,
                            allexistingdynamic=True,
                            allnewdynamic=True,
                            sectorfiles=sectorfiles,
                            start_datetime = start_datetime, 
                            end_datetime=end_datetime,
                            one_per_sector=False,
                            quiet=quiet)
        log.info('pass prediction sectorfile: '+str(sector_file))
    elif not sectorlist:
        sectorlist=[sn.lower() for sn in sector_file.sectornames()]

    if not sensors:
        sensors = []
        for sat in satellites:
            sensors.extend(all_sensors_for_sat(sat))

    log.info('sectorlist in pass_prediction: '+str(sectorlist))


    mins_per_file = {}
    cutofflengths = {}
    km_per_min = {}
    goodsats = []
    log.info('satellites: '+str(satellites))
    log.info('sensors: '+str(sensors))
    for sat in satellites:
        printme = 'sat: '+sat
        mins_per_file[sat] = {}
        km_per_min[sat] = {}
        for sensor in sensors:
            sensor = sensor.lower()
            try:
                #log.info('sat/sensor: '+sat+'/'+sensor)
                #sensor_info = get_sensor_info(sat, sensor)
                sensor_info = SatSensorInfo(sat, sensor)
                if sensor_info.geostationary:
                    printme+= '  RUN ALL GEOSTATIONARY'
                    goodsats.append(sat)
                    continue
                #If no orbital period defined, do not try to predict overpasses
                if not sensor_info.orbital_period:
                    printme+= '  Not geostationary and no orbital period defined - do not run pass predictor'
                    continue
                printme+='  sensor: '+sensor_info.sensorname
                #mins_per_file[sat][sensor] = sensor_info['mins_per_file']
                mins_per_file[sat][sensor] = sensor_info.mins_per_file
                #log.info(mins_per_file[sat][sensor])
                # Be generous.  270 instead of 360
                #deg_lat_per_min[sat][sensor] = 270.0 / float(sensor_info['orbit_period_min'])
                #deg_lat_per_min[sat][sensor] = 270.0 / (float(sensor_info.orbital_period)/60.0)
                # circumference of the earth ~41000km. Use km_per_min instead of 
                # deg_lat_per_min - more direct, and don't have to wait for get_lon_lats
                # Conservative to get wider opass times - 38K not 41K
                km_per_min[sat][sensor] = 38000 / (float(sensor_info.orbital_period)/60.0)
                #cutofflengths[sat] = int(sensor_info['cutofflength'])
                cutofflengths[sat] = int(sensor_info.cutofflength)
                if sat not in goodsats:
                    goodsats.append(sat)
            # Skip satellites that don't have these defined. 
            # Add info if you want to run pass predictor  
            except SatInfoError:
                #log.warning(str(resp)+' Missing satellite_info for '+sat+' / '+sensor)
                continue
        log.info(printme)
    satellites = goodsats

    log.info(cutofflengths)

#    if not cutofflengths:
#        # If 
#        return []

    #Gather basic info
    pid = str(os.getpid())
    num_lines = 1024
    num_samps = 1024

    #Get current date and set up start time
    now = datetime.utcnow() 
    log.info('Current date: %s' % now.strftime('%Y/%m/%d %H:%M:%S'))
    [start_datetime,end_datetime] = time_range_defaults(start_datetime,end_datetime)

    if force == False:
        log.debug('start_datetime: '+str(start_datetime)+' end_datetime: '+str(end_datetime))
        comb_opasses = get_pass_prediction_list(satellites,start_datetime,end_datetime,single,cutofflengths,sectorlist=sectorlist)
        log.debug('start_datetime: '+str(start_datetime)+' end_datetime: '+str(end_datetime))
#        if sectorlist != None:
#            log.info('Sectorlist specified - not using pregenerated pass prediction files, running pass predictor on only passed sectors: '+str(sectorlist))
        if comb_opasses:
            return comb_opasses
        else:
            log.interactive('FOUND NO OVER PASSES IN PASS PREDICTION LIST!  Rerunning pass predictor')

    num_hours = (end_datetime - start_datetime).total_seconds() / 3600

    #Read sectorfile

    # This doesn't actually do anything...
    #vsf = os.getenv('VIIRS_SECTORFILE')
    #if not os.path.exists(os.path.dirname(vsf)): 
    #    log.info('directory did not exist, creating '+os.path.dirname(vsf))
    #    os.makedirs(os.path.dirname(vsf))
    #flatsf = open(vsf,'w')

    max_km = {}
    swath_lons = {}
    swath_lats = {}
    midlat = {}
    sector_width_km = {}
    sector_height_km = {}
    for sect in sector_file.itersectors():
        sectorname = sect.name
        if sectorlist and sectorname.lower() not in [ss.lower() for ss in sectorlist]:
            continue
        if not sect.isactive:
            log.interactive('   CONTINUE1 '+sectorname+' is not active, skipping')
            continue
        if not set([sens.lower() for sens in sensors]) & set([sr.lower() for sr in sect.source_list]):
            log.interactive('   CONTINUE1 sensors '+str(sensors)+' not required for '+sectorname+': '+str(sect.source_list)+', skipping')
            continue
        sect_ad = sect.area_definition
        corners = sect_ad.corners
        clon = sect_ad.proj_dict['lon_0']
        if clon < 0: 
            clon += 360
        clat = sect_ad.proj_dict['lat_0']
        #minlat = sect_ad.area_extent_ll[1]
        #maxlat = sect_ad.area_extent_ll[3]
        #lats = sect_ad.get_lonlats()[1]
        # MLS 20151202 This was failing over the poles arctic sector 
        # had 31 for min and 31 for max, which made num minutes 0...
        # Still proably needs additional tweaking, and get_lonlats is 
        # kind of slow...
        # MLS 20151203 Replaced with max_km, instead of latdiff for 
        # estimating time.
        #minlat = lats.min()
        #maxlat = lats.max()
        ul_corner = corners[0]
        ur_corner = corners[1]
        lr_corner = corners[2]
        ll_corner = corners[3]
        ulcrnlon = math.degrees(ul_corner.lon) 
        urcrnlon = math.degrees(ur_corner.lon)
        llcrnlon = math.degrees(ll_corner.lon) 
        lrcrnlon = math.degrees(lr_corner.lon)
        if lrcrnlon < 0 or llcrnlon < 0 or urcrnlon < 0 or ulcrnlon < 0:
            lrcrnlon += 360
            llcrnlon += 360
            urcrnlon += 360
            ulcrnlon += 360

        lrcrnlat = math.degrees(lr_corner.lat)
        urcrnlat = math.degrees(ur_corner.lat)
        ulcrnlat = math.degrees(ul_corner.lat)
        llcrnlat = math.degrees(ll_corner.lat)
        # L 21 11 22 C 23 12 24 R
        lmidlon = (ulcrnlon + llcrnlon) / 2
        rmidlon = (urcrnlon + lrcrnlon) / 2
        mid1lon1 = (lmidlon + clon) / 2
        mid1lon2 = (clon + rmidlon) / 2
        mid2lon1 = (lmidlon + mid1lon1) / 2 
        mid2lon2 = (mid1lon1 + clon) / 2 
        mid2lon3 = (clon + mid1lon2) / 2 
        mid2lon4 = (mid1lon2 + rmidlon) / 2 
        if mid1lon1 > 180:
            mid1lon1 -= 360
        if mid1lon2 > 180:
            mid1lon2 -= 360
        if clon > 180:
            clon -= 360
        if lmidlon > 180:
            lmidlon -= 360
        if rmidlon > 180:
            rmidlon -= 360
        if mid2lon1 > 180:
            mid2lon1 -= 360
        if mid2lon2 > 180:
            mid2lon2 -= 360
        if mid2lon3 > 180:
            mid2lon3 -= 360
        if mid2lon4 > 180:
            mid2lon4 -= 360
    

        # Can't just use same lat for all mid points - does not work for big stereo sectors !!!
        # Not sure if this was necessary - may have been more the -= / += 360 thing...
        # But I guess this can't hurt ?
        # L 21 11 22 C 23 12 24 R
        lmidlat = (ulcrnlat + llcrnlat) / 2
        rmidlat = (urcrnlat + lrcrnlat) / 2
        mid1lat1 = ( lmidlat + clat ) / 2
        mid1lat2 = ( rmidlat + clat ) / 2
        mid2lat1 = ( mid1lat1 + lmidlat) / 2
        mid2lat2 = ( mid1lat1 + clat) / 2
        mid2lat3 = ( mid1lat2 + clat) / 2
        mid2lat4 = ( mid1lat2 + rmidlat) / 2
   
        sector_width_km[sectorname] = (sect_ad.x_size * sect_ad.pixel_size_x) / 1000.0
        sector_height_km[sectorname] = (sect_ad.y_size * sect_ad.pixel_size_y) / 1000.0
        # MLS 20151203 Use diagonal instead of width or height for maximum distance the swath
        # could cover - might work better for polar, which can be sideways
        max_km[sectorname] = (sector_width_km[sectorname]**2 + sector_height_km[sectorname]**2)**.5
        log.info('Setting up area definition  dictionaries for '+sectorname+' sector height: '+str(sector_height_km[sectorname])+' sector width: '+str(sector_width_km[sectorname])+' diagonal (max_km): '+str(max_km[sectorname]))
        midlat[sectorname] = sect_ad.proj_dict['lat_0']
        swath_lons[sectorname] = [clon,lmidlon,rmidlon,mid1lon1,mid1lon2,mid2lon1,mid2lon2,mid2lon3,mid2lon4]
        swath_lats[sectorname] = [clat,lmidlat,rmidlat,mid1lat1,mid1lat2,mid2lat1,mid2lat2,mid2lat3,mid2lat4]
        log.info(swath_lons)


    #log.interactive(satellites)
    for pp in ['pyephem']:
        log.info('\n\n    '+pp)
        all_passes = []
        sensor_swath_widths = {}
        for sat in satellites:
            log.info('\n\n\n\n')
            day_count = int(math.ceil(num_hours / 24.0))
            for n in range(0,day_count,5): 
                dt = end_datetime-timedelta(n)
                log.info(str(n)+' '+str(dt)+' '+str(sat))
                op,tle = open_predictor(pp,sat,dt)
                #print 'op: '+str(op)+' tle: '+str(tle)
                if not op and not tle:
                    continue
                for sensor in sensors:
                    #print 'sat: '+sat+' sensor: '+sensor
                    try:
                        #si = get_sensor_info(sat,sensor)
                        si = SatSensorInfo(sat,sensor)
                    except SatInfoError:
                        #log.info('get_sensor_info failed for '+sat+' / '+sensor)
                        continue
                    #mins_per_file = si['mins_per_file']
                    try:
                        mins_per_file = si.mins_per_file
                    except AttributeError:
                        # Geo
                        mins_per_file = None
        #Loop over sectors
                    #log.info(sector_file)
                    for sect in sector_file.itersectors():
                        log.info(sect.name)
                        if sat+sect.name not in sensor_swath_widths:
                            sensor_swath_widths[sat+sect.name] = []
                        sector_name = sect.name_info.desig
                        sector_short_name = sect.name
                        try:
                            dynamic_datetime = sect.dynamic_datetime
                        except ValueError:
                            dynamic_datetime = None
                        #if sect.isactive is False:
                        #  log.info('   CONTINUE Sector %s is not specified as active, skipping' % sector_short_name)
                        #  continue
                        sftime_str = ''
                        if dynamic_datetime:
                            #print end_datetime
                            if dynamic_datetime > end_datetime:
                                continue
                            sftime_str = ' sf time: '+str(dynamic_datetime)
                            #log.debug('    TRY Sector '+sector_name.lower()+' '+sector_short_name.lower()+sftime_str)
                            log.info('    TRY Sector '+sector_name.lower()+' '+sector_short_name.lower()+sftime_str)
                        else:
                            #log.debug('    TRY Sector '+sector_name.lower()+' '+sector_short_name.lower())
                            log.info('    TRY Sector '+sector_name.lower()+' '+sector_short_name.lower())
                        if sectorlist is not None and (sector_name.lower() not in sectorlist and sector_short_name.lower() not in sectorlist):
                            log.debug('   CONTINUE sectorlist was specified on command line ('+str(sectorlist)+'), and %s was not included' % sector_short_name)
                            continue
    
                        if sect.isactive is False:
                            log.info('   CONTINUE Sector '+sector_short_name+' is not active, skipping')
                            continue
                        if not set([sens.lower() for sens in sensors]) & set([sr.lower() for sr in sect.source_list]):
                            log.interactive('   CONTINUE sensors '+str(sensors)+' not required for '+sector_short_name+': '+str(sect.source_list)+', skipping')
                            continue

                        #if sector_short_name.lower() == 'montereytest':
                        #    log.interactive(sensor_swath_widths[sat+sect.name])
                        if not dynamic_datetime and sensor_info.swath_width_km in sensor_swath_widths[sat+sect.name]:
                            continue
                        sensor_swath_widths[sat+sect.name] += [sensor_info.swath_width_km]
                        
    
                        #log.info('    RUNNING '+pp+' Sector '+sector_name.lower()+' '+sector_short_name.lower()+sftime_str+' '+'clat: '+str(midlat[sector_short_name])+' clon: '+str(swath_lons[sector_short_name][0])+' width: '+str(sector_width_km[sector_short_name])+'km  km_per_min: '+str(km_per_min[sat][sensor]))
                        log.info('    RUNNING '+pp+' Sector '+sector_name.lower()+' '+sector_short_name.lower()+sftime_str+' '+'clat: '+str(midlat[sector_short_name])+' clon: '+str(swath_lons[sector_short_name][0])+' width: '+str(sector_width_km[sector_short_name])+'km')
                        #if sector_short_name.lower() == 'montereytest':
                        #    log.interactive('    RUNNING '+pp+' dt: '+str(dt)+' sat: '+sat+' sensor: '+sensor+' Sector: '+sector_name.lower()+' '+sector_short_name.lower()+sftime_str+' '+'clat: '+str(midlat[sector_short_name])+' clon: '+str(swath_lons[sector_short_name][0])+' width: '+str(sector_width_km[sector_short_name])+'km swath width: '+str(sensor_info.swath_width_km))
                        # Take out mins_per_file in estimated time
                        # MLS 20151203 Replaced latdiff/deg_lat_per_min with max_km/km_per_min
                        # Work better for polar, which can cross the sector in any direction
                        try:
                            curr_num_hours = (sect.dynamic_endtime - \
                                    sect.dynamic_datetime).total_seconds() / 3600
                            curr_start_datetime = sect.dynamic_datetime
                        except (IndexError,ValueError):
                            curr_num_hours = int(num_hours+1)
                            curr_start_datetime = start_datetime
                        try:
                            est_time = (max_km[sector_short_name] / km_per_min[sat][sensor])
                        except KeyError:
                            # Geo
                            est_time = curr_num_hours*60

    
                        # MLS need to get mins_per_file before the start time of 
                        # overpass (so if it's during the file, we use that file)

                        #MLS 20150415 Pass all_passes to get_overpasses so it can clean up the 
                        # overlapping dynamic sectors. This might have been what 
                        # was slowing things down before.. ?  Probably should check 
                        # on it.  We were missing a bunch of dynamic sectors before
                        # because it was 
                        all_passes = get_overpasses(pp,
                                    sat,
                                    sect,
                                    si,
                                    sector_width_km[sector_short_name],
                                    curr_start_datetime,
                                    end_datetime,
                                    curr_num_hours,
                                    midlat[sector_short_name],
                                    swath_lons[sector_short_name],
                                    swath_lats[sector_short_name],
                                    swath_lons[sector_short_name][0],
                                    mins_per_file,
                                    est_time,
                                    dynamic_datetime,
                                    passes = all_passes,
                                    tle=tle,
                                    op=op,
                                    )

                        #log.interactive('overpasses:'+bigindent+bigindent.join(str(xx) for xx in passes))
                    


                        #num_passes=0
                        #if passes:
                        #    num_passes = len(passes)
                        #    try:
                        #        all_passes.extend(passes)
                        #    except NameError:
                        #        all_passes = passes
  
                        
                        log.info('%r passes were predicted so far for %r hour period starting on %s.' % 
                                    (len(all_passes), num_hours, start_datetime))


    #flatsf.close()

    #log.info('\n\n\n\nAll overpasses:')
    #for opass in all_passes:
    #    log.info(str(opass))
    if both or not single:
        log.info('combine_overpasses 1')
        all_passes = combine_overpasses(all_passes,cutofflengths,individual=True)

        log.info('combine_overpasses 2')
        combined_passes = combine_overpasses(all_passes,cutofflengths)

        #log.info('Combined overpasses:'+bigindent+bigindent.join(sorted(str(val) for val in combined_passes))+'\n')

    if both:
        return (all_passes,combined_passes)
    if single:
        return all_passes
    return combined_passes

def combine_overpasses(passes,cutofflengths=None,individual=False):
    if len(passes) == 0:
        return passes
    if individual:
        log.info('sorting by dt then sectornames')
        sorted_passes = sorted(passes,key=operator.attrgetter('basedt'),reverse=True)
        sorted_passes = sorted(sorted_passes,key=operator.attrgetter('sectornames'))
        # Make sure this stays commented out - can slow things down a lot when we 
        # are dealing with a lot of sectors. I think...
        #for op in sorted_passes:
        #    log.info(str(op))
    else:
        log.info('sorting by dt then satellite_name')
        sorted_passes = sorted(passes,key=operator.attrgetter('basedt'),reverse=True)
        sorted_passes = sorted(sorted_passes,key=operator.attrgetter('satellite_name'),reverse=True)
    log.info('done sorting'+str(len(sorted_passes)))
    old_opass = sorted_passes.pop(0)
    last_opass = old_opass
    new_opasses = []
    for opass in sorted_passes:
        #print 'checking: individual: '+str(individual)+' '+str(opass)+' '+str(old_opass)+' cutofflengths: '+str(cutofflengths[opass.satellite_name])
        if not individual and cutofflengths != None and opass.satellite_name in cutofflengths.keys():
            #print 'combining with not individual and cutofflengths != None'
            curr_new_opasses = opass.combine(old_opass,cutofflengths[opass.satellite_name])
        elif individual:
            #print 'combining with individual'
            curr_new_opasses = opass.combine(old_opass,cutofflength=90,individual=True)
        else:
            #print 'combining with no cut off time'
            curr_new_opasses = opass.combine(old_opass)
        try:
            #log.debug(curr_new_opasses[1])
            new_opasses.append(curr_new_opasses[1])
            old_opass = opass
            #last_opass = None
            #log.debug('new_opasses now:')
            # Make sure this stays commented out, it can slow things 
            # down a lot if we are looping through within the loop, 
            # even if it's not doing anything. I think...
            #for new_opass in new_opasses:
            #    log.info('                NEWOPASS'+str(new_opass))
            last_opass = opass
        except (AttributeError,TypeError):
            old_opass = curr_new_opasses
            last_opass = curr_new_opasses

    if last_opass != None:
        new_opasses.append(last_opass)
        log.debug('Last one was combined - need to append to end '+str(last_opass))
    #for new_opass in new_opasses:
    #    log.info('                '+str(new_opass))
 
    return new_opasses

def latlon_to_float(num):
    try:
        if num[-1] in ['N', 'S', 'E', 'W']:
            if num[-1] in ['N', 'E']:
                return float(num[:-1])
            else:
                return (-1)*float(num[:-1])
        else:
            raise TypeError()
    except TypeError:
        return num
        
if __name__ == '__main__':
    root_logger,file_hndlr,email_hndlr = root_log_setup(loglevel=logging.INFO,subject='pass_prediction')

    parser = argparse.ArgumentParser()
    parser.add_argument('satellite', help='Pass a list of satellites to include in pass prediction list')
    parser.add_argument('sensor', help='Pass a list of sensors to include')
    parser.add_argument('--nofit', action='store_true')
    parser.add_argument('-s', '--sectorlist', default=None)
    parser.add_argument('-S','--start_datetime',nargs='?',default=None)
    parser.add_argument('-E','--end_datetime',nargs='?',default=None)
    parser.add_argument('-B','--num_hours_back_to_start',nargs='?',default=None)
    parser.add_argument('-N','--num_hours_to_check',nargs='?',default=None)
    parser.add_argument('--sectorfiles',nargs='?',default=[])
    parser.add_argument('--templatefiles',nargs='?',default=[])
    parser.add_argument('--allstatic',action='store_true')
    parser.add_argument('--alldynamic',action='store_true')
    parser.add_argument('--tc',action='store_true')
    parser.add_argument('--volcano',action='store_true')
    args = parser.parse_args()

    [args.start_datetime,args.end_datetime] = time_range_defaults(
                            args.start_datetime,
                            args.end_datetime,
                            args.num_hours_back_to_start,
                            args.num_hours_to_check)

    args.satellite = args.satellite.split()
    args.sensor = args.sensor.split()

    if args.sectorlist is not None:
        args.sectorlist = args.sectorlist.split()

    if args.sectorfiles:
        args.sectorfiles = args.sectorfiles.split()
        log.info('Doing static files:')
        log.info(args.sectorfiles)

    if args.templatefiles:
        args.templatefiles = args.templatefiles.split()
        log.info('Doing dynamic files:')
        log.info(args.templatefiles)

    combined_sf = sectorfile.open(
                        sectorfiles = args.sectorfiles,
                        dynamic_templates = args.templatefiles,
                        tc = args.tc,
                        volcano = args.volcano,
                        allstatic = args.allstatic,
                        alldynamic = args.alldynamic,
                        start_datetime = args.start_datetime,
                        end_datetime = args.end_datetime,
                        one_per_sector = True)
    log.info('sector file now contains:'+bigindent+bigindent.join(combined_sf.names))

    pass_prediction(
        args.satellite, 
        args.sensor,
        combined_sf,
        args.sectorlist,
        args.start_datetime,
        args.end_datetime,
        no_fit=args.nofit)
