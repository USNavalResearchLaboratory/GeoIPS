#!/usr/bin/env python

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
import smtplib
from email.mime.text import MIMEText
import re
import os
import socket
import logging
import commands
from glob import glob
from datetime import datetime,timedelta
import filecmp
import sqlite3


# Installed Libraries
from lxml import etree
from IPython import embed as shell
from lxml import objectify
from pyresample import spherical_geometry


# GeoIPS Libraries
import geoips.sectorfile
import geoips.utils.plugin_paths as plugins
from geoips.utils.path.filename import _FileNameBase
from geoips.utils.log_setup import interactive_log_setup
from geoips.utils.xml_utilities import DTDMissing
from geoips.utils.path.path import Path


log = interactive_log_setup(logging.getLogger(__name__))

atcf_decks_db = plugins.paths['SATOPS']+'/longterm_files/atcf/atcf_decks.db'
atcf_decks_dir = plugins.paths['SATOPS']+'/longterm_files/atcf/decks'

def open_db(db=atcf_decks_db):

    # Make sure the directory exists.  If the db doesn't exist,
    # the sqlite3.connect command will create it - which will
    # fail if the directory doesn't exist.
    if not os.path.exists(os.path.dirname(db)):
        os.makedirs(os.path.dirname(db))

    conn = sqlite3.connect(db)
    cc = conn.cursor()
    # Try to create the table - if it already exists, it will just fail 
    # trying to create, pass, and return the already opened db.
    try:
    	cc.execute('''CREATE TABLE atcf_deck_stormfiles
            (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                filename text, 
                last_updated timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
                storm_num integer,
                storm_basin text,
                start_datetime timestamp, 
                start_lat real, 
                start_lon real, 
                start_vmax real, 
                start_name real, 
                vmax real, 
                end_datetime timestamp)''')
                # Add in at some point?
                #storm_start_datetime timestamp, 
    except sqlite3.OperationalError:
        pass
    return cc,conn

def update_fields(atcf_stormfilename,cc,conn,process=False):
    # Must be of form similar to 
    # Gal912016.dat

    updated_files = []

    log.info('Checking '+atcf_stormfilename+' ... process '+str(process))

    # Check if we match Gxxdddddd.dat filename format. If not just return and don't do anything.
    if not re.compile('G\D\D\d\d\d\d\d\d\.\d\d\d\d\d\d\d\d\d\d.dat').match(os.path.basename(atcf_stormfilename)) and \
        not re.compile('G\D\D\d\d\d\d\d\d\.dat').match(os.path.basename(atcf_stormfilename)): 
        log.info('')
        log.warning('    DID NOT MATCH REQUIRED FILENAME FORMAT, SKIPPING: '+atcf_stormfilename)
        return []

    # Get all fields for the database entry for the current filename
    cc.execute("SELECT * FROM atcf_deck_stormfiles WHERE filename = ?", (atcf_stormfilename,))
    data=cc.fetchone()

    file_timestamp = datetime.fromtimestamp(os.stat(atcf_stormfilename).st_mtime)
    # Reads timestamp out as string - convert to datetime object.
    # Check if timestamp on file is newer than timestamp in database - if not, just return and don't do anything.
    if data: 
        database_timestamp = datetime.strptime(cc.execute("SELECT last_updated from atcf_deck_stormfiles WHERE filename = ?", (atcf_stormfilename,)).fetchone()[0],'%Y-%m-%d %H:%M:%S.%f')
        if file_timestamp < database_timestamp:
            log.info('')
            log.info(atcf_stormfilename+' already in '+atcf_decks_db+' and up to date, not doing anything.')
            return []

    lines = open(atcf_stormfilename,'r').readlines()
    start_line = lines[0].split(',')
    # Start 24h prior to start in sectorfile, for initial processing
    #storm_start_datetime = datetime.strptime(start_line[2],'%Y%m%d%H')
    start_datetime = datetime.strptime(start_line[2],'%Y%m%d%H') - timedelta(hours=24)
    end_datetime = datetime.strptime(lines[-1].split(',')[2],'%Y%m%d%H')
    start_vmax= start_line[8]
    vmax=0
    for line in lines:
        currv = line.split(',')[8]
        track = line.split(',')[4]
        if currv and track == 'BEST' and float(currv) > vmax:
            vmax = float(currv)

    if data and database_timestamp < file_timestamp:
        log.info('')
        log.info('Updating start/end datetime and last_updated fields for '+atcf_stormfilename+' in '+atcf_decks_db)
        old_start_datetime,old_end_datetime,old_vmax = cc.execute("SELECT start_datetime,end_datetime,vmax from atcf_deck_stormfiles WHERE filename = ?", (atcf_stormfilename,)).fetchone()
        # Eventually add in storm_start_datetime
        #old_storm_start_datetime,old_start_datetime,old_end_datetime,old_vmax = cc.execute("SELECT storm_start_datetime,start_datetime,end_datetime,vmax from atcf_deck_stormfiles WHERE filename = ?", (atcf_stormfilename,)).fetchone()
        if old_start_datetime == start_datetime.strftime('%Y-%m-%d %H:%M:%S'):
            log.info('    UNCHANGED start_datetime: '+old_start_datetime)
        else:
            log.info('    Old start_datetime: '+old_start_datetime+' to new: '+start_datetime.strftime('%Y-%m-%d %H:%M:%S'))
            updated_files += [atcf_stormfilename]
        #if old_storm_start_datetime == storm_start_datetime.strftime('%Y-%m-%d %H:%M:%S'):
        #    log.info('    UNCHANGED storm_start_datetime: '+old_storm_start_datetime)
        #else:
        #    log.info('    Old storm_start_datetime: '+old_storm_start_datetime+' to new: '+storm_start_datetime.strftime('%Y-%m-%d %H:%M:%S'))
        if old_end_datetime == end_datetime.strftime('%Y-%m-%d %H:%M:%S'):
            log.info('    UNCHANGED end_datetime: '+old_end_datetime)
        else:
            log.info('    Old end_datetime: '+old_end_datetime+' to new: '+end_datetime.strftime('%Y-%m-%d %H:%M:%S'))
            updated_files += [atcf_stormfilename]
        if database_timestamp == file_timestamp:
            log.info('    UNCHANGED last_updated: '+database_timestamp.strftime('%Y-%m-%d %H:%M:%S'))
        else:
            log.info('    Old last_updated: '+database_timestamp.strftime('%Y-%m-%d %H:%M:%S')+' to new: '+file_timestamp.strftime('%Y-%m-%d %H:%M:%S'))
            updated_files += [atcf_stormfilename]
        if old_vmax == vmax:
            log.info('    UNCHANGED vmax: '+str(old_vmax))
        else:
            log.info('    Old vmax: '+str(old_vmax)+' to new: '+str(vmax))
            updated_files += [atcf_stormfilename]
        cc.execute('''UPDATE atcf_deck_stormfiles SET 
                        last_updated=?,
                        start_datetime=?,
                        end_datetime=?,
                        vmax=? 
                      WHERE filename = ?''', 
                      #Eventually add in ?
                      #storm_start_datetime=?,
                        (file_timestamp,
                        #storm_start_datetime,
                        start_datetime,
                        end_datetime,
                        str(vmax),
                        atcf_stormfilename,))
        conn.commit()
        log.info('Creating dynamic xml sectorfiles')
        create_dynamic_xml_sectorfiles_from_deckfile(atcf_stormfilename, force_update=True)
        return updated_files

    start_lat = start_line[6]
    start_lon = start_line[7]
    storm_basin = start_line[0]
    storm_num = start_line[1]
    try:
        start_name= start_line[48]+start_line[49]
    except IndexError:
        start_name= start_line[41]

    if data == None:
        #print '    Adding '+atcf_stormfilename+' to '+atcf_decks_db
        cc.execute('''insert into atcf_deck_stormfiles(
                        filename,
                        last_updated,
                        vmax,
                        storm_num,
                        storm_basin,
                        start_datetime,
                        start_lat,
                        start_lon,
                        start_vmax,
                        start_name,
                        end_datetime) values(?, ?,?, ?,?,?,?,?,?,?,?)''', 
                        # Eventually add in ?
                        #end_datetime) values(?, ?, ?,?, ?,?,?,?,?,?,?,?)''', 
                        #storm_start_datetime,
                        (atcf_stormfilename,
                            file_timestamp,
                            str(vmax),
                            storm_num,
                            storm_basin,
                            #storm_start_datetime,
                            start_datetime,
                            start_lat,
                            start_lon,
                            start_vmax,
                            start_name,
                            end_datetime,))
        log.info('')
        log.info('    Adding '+atcf_stormfilename+' to '+atcf_decks_db) 
        updated_files += [atcf_stormfilename]
        conn.commit()
        log.info('Creating dynamic xml sectorfiles')
        create_dynamic_xml_sectorfiles_from_deckfile(atcf_stormfilename, force_update=True)

        # This ONLY runs if it is a brand new storm file and we requested 
        # processing.
        if process:
            reprocess_storm(atcf_stormfilename)
    return updated_files

def reprocess_storm(atcf_stormfilename):
    sectors = parse_atcf_storm(atcf_stormfilename,None)

    startstormsect = sectors[0]
    endstormsect = sectors[-1]

    # Let's use values from database...
    startdt,enddt = get_all_from_db(
        stormfilename=atcf_stormfilename,fields=['start_datetime','end_datetime'])
        
    #startdt,enddt,stormstartdt = get_all_from_db(stormfilename=atcf_stormfilename,fields=['start_datetime','end_datetime','storm_start_datetime'])
    startdt = datetime.strptime(startdt,'%Y-%m-%d %H:%M:%S')
    #stormstartdt = datetime.strptime(stormstartdt,'%Y-%m-%d %H:%M:%S')
    enddt = datetime.strptime(enddt,'%Y-%m-%d %H:%M:%S')
    #startdt = startstormsect.dynamic_datetime
    #enddt = endstormsect.dynamic_datetime

    # Added the prior 24h to parse_atcf_storm, but it appears
    # to only create the temporary xml sectorfiles (but here
    # doesn't return sector[0] the T-24 time ?).
    # Seems to work for now, might want to look into it at
    # some point... Adding it to parse_atcf_storm made it so
    # it would actually find something to process in the 
    # prior 24h (but we still have to explicitly request the
    # prior 24h here)
    #startdt = startstormdt - timedelta(hours=24)
    # This was not finding the storm in the database prior to storm
    # start datetime. This is probably going to have negative   
    # consequences, but we will see...

    datelist = [startdt.strftime('%Y%m%d')]
    for nn in range((enddt - startdt).days + 2):
        datelist += [(startdt + timedelta(nn)).strftime('%Y%m%d')]

    hourlist = []
    for ii in range(24):
        hourlist += [(enddt-timedelta(hours=ii)).strftime('%H')]
    hourlist.sort()
    # Do newest first
    datelist.sort(reverse=True)

    log.interactive('Running process_overpass for storm '+startstormsect.name+' from '+datelist[0]+' to '+datelist[-1])
    log.interactive('    start datetime: '+str(startdt))
    log.interactive('    end datetime: '+str(enddt))
    log.interactive(get_all_from_db(stormfilename=atcf_stormfilename))

    sector_file = geoips.sectorfile.open(alldynamic=True,
                    tc=True,
                    start_datetime=startdt,
                    end_datetime=enddt,
                    sectorlist=[startstormsect.name],
                    one_per_sector=False,
                    quiet=True)
    from geoips.process_overpass import process_overpass
    for sat,sensor in [('gcom-w1','amsr2'),
                            ('gpm','gmi'),
                            ('npp','viirs'),
                            ('aqua','modis'),
                            ('terra','modis'),
                            ('himawari8','ahi'),
                            ('goesE','gvar'),
                            ('goesW','gvar')
                            ]:
        for datestr in datelist:
            process_overpass(sat,sensor,
                productlist=None,
                sectorlist=[startstormsect.name],
                sectorfiles=None,
                extra_dirs=None,
                sector_file=sector_file,
                datelist=[datestr],
                hourlist=hourlist,
                queue=os.getenv('DEFAULT_QUEUE'),
                mp_max_cpus=3,
                allstatic=False,
                alldynamic=True,
                # list=True will just list files and not actually run
                #list=True,
                list=False,
                quiet=True,
                start_datetime = startdt,
                end_datetime = enddt,
                )
    #shell()

def add_to_db(atcf_stormfilename):


    cc,conn = open_db()

    update_fields(atcf_stormfilename,cc,conn)

    cc.execute("SELECT * FROM atcf_deck_stormfiles WHERE filename = ?", (atcf_stormfilename,))
    data = cc.fetchone()
    conn.close()
    log.info('')
    return data

def check_db(filenames=[atcf_decks_dir],process=False):
    '''filenames is a list of filenames and directories.
        if a list element is a string directory name, it expands to list of files in dir'''

    updated_files = []
    cc,conn = open_db()

    # We might want to rearrange this so we don't open up every file... Check timestamps first.
    for filename in filenames:
        if os.path.dirname(filename):
            more_filenames = glob(filename+'/*')
            for more_filename in more_filenames:
                updated_files += update_fields(more_filename,cc,conn,process=process)
        else:
            updated_files += update_fields(filename,cc,conn,process=process)

    cc.execute("SELECT * FROM atcf_deck_stormfiles")
    data = cc.fetchall()
    conn.close()
    #return data
    return updated_files

def get_all_from_db(stormfilename=None,fields=None):

    # Do not do anything if the database doesn't exist.
    if not os.path.exists(atcf_decks_db):
        return []
    cc,conn = open_db()

    if not fields and not stormfilename:
        cc.execute("SELECT * FROM atcf_deck_stormfiles")
        data = cc.fetchall()
    elif stormfilename and not fields:
        cc.execute('SELECT * from atcf_deck_stormfiles WHERE filename = ?', (stormfilename,))
        data = cc.fetchall()
    elif stormfilename and fields:
        cc.execute('SELECT '+','.join(fields)+' from atcf_deck_stormfiles WHERE filename=?', (stormfilename,))
        data = cc.fetchone()
    conn.close()
    return data

def remove_entry(atcf_stormfilename):
    cc,conn = open_db()
    log.info('Removing '+atcf_stormfilename+' from database...')
    cc.execute('''DELETE FROM atcf_deck_stormfiles WHERE filename = ?''', (atcf_stormfilename,))
    log.info('    Removed '+str(conn.total_changes)+' total entries from database!')
    conn.commit()
    conn.close()
    

def get_timerange_from_db(start_datetime,end_datetime):

    # Do not do anything if the database doesn't exist.
    if not os.path.exists(atcf_decks_db):
        return []
    cc,conn = open_db()

    log.info('get_timerange')
    #cc.execute("SELECT * FROM atcf_deck_stormfiles WHERE start_datetime between ? and ?", (start_datetime,end_datetime))
    cc.execute('''SELECT * FROM atcf_deck_stormfiles 
                WHERE end_datetime between ? and ? 
                    OR start_datetime between ? and ? 
                    OR (start_datetime <= ? AND end_datetime >= ?)''', 
                (start_datetime,
                end_datetime,
                start_datetime,
                end_datetime,
                start_datetime,
                end_datetime))
    data = cc.fetchall()
    conn.close()
    return data

#def update_sector(sector,dynamic_templatefname):

def choose_dynamic_xml_sectorfiles(str_current_sectorfiles,
                                start_datetime,
                                end_datetime,
                                actual_datetime=None,
                                sectorlist=None,
                                one_per_sector=True,
                                include_static=True):
    # You must pass the complete range of time you want sectorfiles
    # chosen from. Used to have 5h slop in this routine, but that 
    # was having unintended consequences for TCs (we didn't want to use
    # sectorfiles after the storm time, because could end up with multiple
    # sectorfiles for the same storm that way)
    log.info('    start_datetime is: '+str(start_datetime))
    log.info('    end_datetime is: '+str(end_datetime))
    if actual_datetime == None:
        actual_datetime =  start_datetime + ((end_datetime - start_datetime)/2)
    log.info('    actual_datetime is: '+str(actual_datetime))

                   
    good_sectorfiles = {} 

#    check_db(str_current_sectorfiles)

#    data = get_timerange(start_datetime,end_datetime)
#    log.info('\n'.join([str(x) for x in data]))

    for str_current_sf in str_current_sectorfiles:
        try:
            current_sf = geoips.sectorfile.open([str_current_sf])
        except (etree.XMLSyntaxError,DTDMissing),resp:
            log.error(str(resp)+'   Something wrong with '+str_current_sf+'!!! Giving up and moving onto the next one'+commands.getoutput('ls --full-time '+str_current_sf)+commands.getoutput('cat '+str_current_sf))
            continue
        if sectorlist != None and current_sf.open_sectors(sectorlist) == None:
            log.debug('            Requested Sectors not in file, skipping: '+' '.join(sectorlist))
            continue
        # Note: if there are bad entries in the sector file, the getsectors method will raise an error
        # We were getting an AssertionError when there was an invalid lon value (>180).  Should probably 
        # Check this when we create the xml file too... but good to have a backup in case something gets
        # through.
        try:
            sectors = current_sf.getsectors()
        except AssertionError,resp:
            log.error(str(resp)+'   Invalid file, SKIPPING sectorfile '+str_current_sf+'!!! Giving up and moving onto the next one'+commands.getoutput('ls --full-time '+str_current_sf)+commands.getoutput('cat '+str_current_sf))
            continue
        sector = sectors[0]
        shortname = sector.name
        if sector.isdynamic == True:
            dt = sector.dynamic_datetime
            # This used to have maxtimediff = timedelta(hours=5). Force start_datetime and end_datetime
            # to cover the full desired range (was screwing up TCs, because it was grabbing sf times
            # after the storm time, when the time range we were passing was 6h before until storm time)
            if _FileNameBase.is_concurrent_with(dt,
                                    other_startdt=start_datetime,
                                    other_enddt=end_datetime) == True:
                # This will fail if xml is up to date.  Will rewrite if template file is newer than xml file
                write_single_dynamic_xml_file(sector)
                if one_per_sector == False:
                    log.debug('        good all: dynamic_datetime for '+os.path.basename(current_sf.name)+' is: '+str(dt))
                    good_sectorfiles[str_current_sf] = str_current_sf
                elif shortname in good_sectorfiles:
                    old_sf = geoips.sectorfile.open([good_sectorfiles[shortname]])
                    old_sectors = old_sf.getsectors()
                    old_sector = old_sectors[0]
                    old_dt = old_sector.dynamic_datetime
                    log.debug('old_dt: '+str(old_dt)+' dt: '+str(dt)+' start_dt: '+str(start_datetime)+' end_dt: '+str(end_datetime))
                    old_timediff = abs(old_dt - actual_datetime)
                    new_timediff = abs(dt - actual_datetime)
                    log.debug('            '+shortname+': old_timediff: '+str(old_timediff)+' new_timediff: '+str(new_timediff))
                    if new_timediff < old_timediff:
                        log.debug('        good replace: dynamic_datetime for '+os.path.basename(current_sf.name)+' is: '+str(dt))
                        good_sectorfiles[shortname] = str_current_sf
                else:
                    log.debug('        good one: dynamic_datetime for '+os.path.basename(current_sf.name)+' is: '+str(dt))
                    good_sectorfiles[shortname] = str_current_sf
        if sector.isdynamic == False and include_static == True:
            log.debug('Sector '+shortname+' is not dynamic and include_static == True, including')
            good_sectorfiles[str_current_sf] = str_current_sf
        
    return good_sectorfiles.values()

def parse_pyrocb(line,dynamic_templatefname,sfname):

    sectors = []

    parts = line.split() 
    tag = parts[0]
    if tag.lower() != 'pyrocb':
        raise ValueError
    pyrocbname = parts[1].replace('_','').replace('.','').replace('-','').replace('/','')
    minlat = parts[2]
    log.info('        minlat'+str(minlat))
    maxlat = parts[3]
    log.info('        maxlat'+str(maxlat))
    minlon = parts[4]
    log.info('        minlon'+str(minlon))
    maxlon = parts[5]
    log.info('        maxlon'+str(maxlon))
    try:
        start_date = datetime.strptime(parts[5],'%Y%m%d')
        end_date = datetime.strptime(parts[6],'%Y%m%d')
    except (ValueError,AttributeError,IndexError):
        start_date = datetime.utcnow() - timedelta(days=2)
        # Do full days
        start_date = datetime.strptime(start_date.strftime('%Y%m%d'),'%Y%m%d')
        end_date = datetime.utcnow() + timedelta(days=4)
        end_date = datetime.strptime(end_date.strftime('%Y%m%d'),'%Y%m%d')
        log.info('        '+str(start_date)+' '+str(end_date))



    earth_radius_km = 6372.795
    #log.info(minlon)
    ul = spherical_geometry.Coordinate(lon=float(minlon),lat=float(maxlat))
    ll = spherical_geometry.Coordinate(lon=float(minlon),lat=float(minlat))
    ur = spherical_geometry.Coordinate(lon=float(maxlon),lat=float(maxlat))
    lat_dist = ul.distance(ll)*earth_radius_km
    lon_dist = ul.distance(ur)*earth_radius_km

    dt = start_date
    new_dt = start_date
    nn = 0

    # Create 2 days worth of pyrocb sector files (every 6h, because that is the default
    # for how long they are valid).  Lame, but haven't decided the best way to define long
    # term dynamic sectors
    while new_dt < end_date+timedelta(days=1):
        dynamic_template_sf = geoips.sectorfile.open([dynamic_templatefname])
        sector = dynamic_template_sf.getsectors()[0]
        #log.info('new_dt end_date'+str(new_dt)+' '+str(end_date))
        nn = nn+1

        sector.name = 'pcb'+pyrocbname+'_active'
    
        sector.area_info.center_lon = (float(minlon)+float(maxlon)) / 2.0
        sector.area_info.center_lat = (float(minlat)+float(maxlat)) / 2.0
        sector.area_info.pixel_width = sector.pyrocb_info.box_resolution_km
        sector.area_info.pixel_height = sector.pyrocb_info.box_resolution_km
        #num_lines/samples must be integer!!
        sector.area_info.num_lines = int(lat_dist / sector.pyrocb_info.box_resolution_km)
        sector.area_info.num_samples = int(lon_dist / sector.pyrocb_info.box_resolution_km)

        sector.name_info.continent = "PyroCB"
        sector.name_info.country = 'x'
        sector.name_info.area = 'x'
        sector.name_info.subarea = pyrocbname+'_active'

        sector.source_info.sourceflattextfile = sfname
        sector.source_info.sourcetemplate = dynamic_templatefname
        sector.source_info.sourceline = line.strip()
        sector.pyrocb_info.minlat = minlat
        sector.pyrocb_info.maxlat = maxlat
        sector.pyrocb_info.minlon = minlon
        sector.pyrocb_info.maxlon = maxlon

        sector.dynamic_datetime=new_dt
        new_dt = dt + timedelta(hours=6*nn)
        sector.dynamic_endtime=new_dt

        try:
            sectors.append(sector)
        except:
            log.exception('Failed')

#    for sector in sectors:
#        log.info(sector.dynamic_datetime)

    return sectors

def parse_volcano(line,dynamic_templatefname,sfname):

    sectors = []

    parts = line.split() 
    wind_speed = parts.pop()
    wind_dir = parts.pop()
    plume_height = parts.pop()
    summit_elevation = parts.pop()
    clon = parts.pop()
    clat = parts.pop()
    time = parts.pop()
    date = parts.pop()
    volcname = ''.join(parts).replace('_','').replace('.','').replace('-','').replace('/','')

    start_date = datetime.strptime(date+time,'%Y%m%d%H%M')

    new_dt = start_date
    nn = 0

    # Create 2 days worth of volcano sector files (every 6h, because that is the default
    # for how long they are valid).  Lame, but haven't decided the best way to define long
    # term dynamic sectors. There were gaps whenever new volcano messages were not sent OUT
    # frequently enough.
    while new_dt < start_date+timedelta(days=2):

        dynamic_template_sf = geoips.sectorfile.open([dynamic_templatefname])
        sector = dynamic_template_sf.getsectors()[0]

        nn = nn+1

        sector.name = 'volc'+volcname+'_active'
        sector.dynamic_datetime=datetime.strptime(date+'.'+time,'%Y%m%d.%H%M')
        
        sector.area_info.center_lat = clat
        sector.area_info.center_lon = clon

        sector.name_info.continent = "Volcanoes"
        sector.name_info.country = 'x'
        sector.name_info.area = 'x'
        sector.name_info.subarea = volcname.upper()+'_active'

        sector.source_info.sourceflattextfile = sfname
        sector.source_info.sourcetemplate = dynamic_templatefname
        sector.source_info.sourceline = line.strip()
        sector.volcano_info.summit_elevation = summit_elevation
        sector.volcano_info.plume_height = plume_height
        sector.volcano_info.wind_speed = wind_speed
        sector.volcano_info.wind_dir = wind_dir
        sector.volcano_info.clat = clat
        sector.volcano_info.clon = clon

        sector.dynamic_datetime=new_dt
        new_dt = start_date + timedelta(hours=6*nn)
        sector.dynamic_endtime=new_dt

        try:
            sectors.append(sector)
        except:
            log.exception('Failed')

    log.debug('      Current Volcano sector: '+line.strip())

    return sectors

def parse_atcf_line(line):
    parts = line.split(',',40)
    fields = {}
    fields['line'] = line.strip()
    fields['basin'] = parts[0]
    fields['stormnum'] = parts[1]
    fields['synoptic_time'] = datetime.strptime(parts[2],'%Y%m%d%H')
    fields['clat'] = parts[6]
    fields['clon'] = parts[7]
    fields['clat'] = float(fields['clat'])
    fields['clon'] = float(fields['clon'])
    fields['wind_speed'] = parts[8]
    if fields['wind_speed']:
        fields['wind_speed'] = float(fields['wind_speed'])
    fields['pressure'] = parts[9]
    if fields['pressure']:
        fields['pressure'] = float(fields['pressure'])

    fields['stormname'] = parts[39]
    return fields

def set_atcf_sector(fields, dynamic_templatefname, finalstormname, tcyear, sfname, dynamic_xmlpath):
    # Note that you HAVE to reopen the dynamic template every time, 
    # or you end up with all the same sectors - the last one overwrites all
    # previous sectors.
    dynamic_template_sf = geoips.sectorfile.open([dynamic_templatefname])
    orig_sector = dynamic_template_sf.getsectors()[0]
    orig_sectorname = orig_sector.name
    sector = dynamic_template_sf.getsectors()[0]

    basin = fields['basin'].lower()
    stormname = finalstormname.lower()
    stormnum = fields['stormnum']
    curryear = int(fields['synoptic_time'].strftime('%Y'))
    currmonth = int(fields['synoptic_time'].strftime('%m'))

    # The time of the dynamic sector should be the time of the DATA
    #if actual_datetime:
    #    sector.dynamic_datetime=actual_datetime
    #else:
    #    sector.dynamic_datetime = fields['synoptic_time']
    # MLS 20170512 actual_datetime breaks pre-gen lat/lons (new runs don't match)
    sector.dynamic_datetime = fields['synoptic_time']

    if orig_sectorname != '':
        newname = basin+stormnum+stormname+'_'+orig_sectorname
    else:   
        newname = basin+stormnum+stormname

    stormnum= fields['stormnum'].replace('_','').replace('.','')
    stormname = fields['stormname'].replace('_','').replace('.','')
    newname = newname.replace('_','').replace('.','')
    # This ends up being tc2016io01one
    sector.name = 'tc'+str(tcyear)+newname

        
    
    # Fill in the fields from the dynamic template sector
    sector.area_info.center_lat = fields['clat']
    sector.area_info.center_lon = fields['clon']

    sector.source_info.sourceflattextfile = sfname
    sector.source_info.sourcetemplate = dynamic_templatefname
    sector.source_info.sourcedynamicxmlpath= dynamic_xmlpath
    sector.source_info.sourceline = fields['line']
    # FNMOC sectorfile doesn't have pressure
    sector.tc_info.pressure = fields['pressure']
    sector.tc_info.wind_speed = fields['wind_speed']
    sector.tc_info.clat = fields['clat']
    sector.tc_info.clon = fields['clon']
    sector.tc_info.dtg = sector.dynamic_datetime
    sector.tc_info.storm_num = fields['stormnum']
    sector.tc_info.storm_name = fields['stormname']

    # Forcing this into old directory naming format. See utils/path/productfilename.py
    sector.name_info.continent = "tc"+str(tcyear)
    sector.name_info.subarea = fields['basin']
    sector.name_info.state = fields['basin']+fields['stormnum']+str(tcyear)
    log.debug('      Current TC sector: '+fields['line'])
    return sector


def parse_atcf_storm(sfname,actual_datetime=None):
    dynamic_xmlpath = plugins.paths['SATOPS']+'/intermediate_files/sectorfiles/atcf_xml'
    dynamic_templatefname = None
    for templatefname in plugins.paths['TEMPLATEPATHS']:
        # Find the one that exists
        if os.path.exists(templatefname+'/template_atcf_sectors.xml'):
            dynamic_templatefname = templatefname+'/template_atcf_sectors.xml'
        # Take the first one
        if dynamic_templatefname:
            continue    

    # Must get tcyear out of the filename in case a storm crosses TC vs calendar years.
    tcyear = os.path.basename(sfname)[5:9]
    #print tcyear

    flatsf_lines = open(sfname).readlines()
    new_fields = []
    beforeinterp = None
    afterinterp = None
    firsttime = True
    finalstormname = 'INVEST'

    # flatsf_lines go from OLDEST to NEWEST (so firsttime is the OLDEST
    # storm location)
    for line in flatsf_lines:
        interp = parse_atcf_line(line)

        # Need to check all of the prior 24h even if actual_datetime specified.
        # It needs to return a sectorfile if we are trying to actually run a 
        # sector on an actual data file - if the prior 24h are not included
        # in the list, it won't be able to return.
        # flatsf_lines go from OLDEST to NEWEST (so firsttime is the OLDEST
        # storm location)
        if firsttime:
            firsttime = False
            # Needed to do this so we would reprocess prior 24h
            # (Before we would try to go back, but there were no
            # sectorfiles, so it wouldn't do anything).
            # start_datetime in database is set in check_db,
            # changed it to be storm start_datetime - 24h.
            # So now start datetime in database should match
            # sectorfiles and prior 24h. Not sure that is what
            # we want...? Thinking about eventually adding 
            # an additional database field for storm_start_datetime
            # flatsf_lines go from OLDEST to NEWEST (so firsttime is the OLDEST
            # storm location)
            for timediff in [6,12,18,24,30]:
                # This will not work for nested dictionaries. Need deepcopy for that.
                currinterp = interp.copy()
                currinterp['synoptic_time'] = interp['synoptic_time'] - timedelta(hours=timediff)
                # If actual_datetime is exactly the synoptic time, then we don't need to interpolate.
                # set before and after to synoptic_time
                if actual_datetime and actual_datetime == currinterp['synoptic_time']:
                    beforeinterp=currinterp.copy()
                    afterinterp = currinterp.copy()
                # When we pass an actual_datetime, we need to get the synoptic time before
                # and the synoptic time after so we can interpolate to the actual datetime
                # of the data. Need to also
                elif actual_datetime and currinterp['synoptic_time'] < actual_datetime:
                    beforeinterp=currinterp.copy()
                new_fields += [currinterp]
            # If we still haven't assigned a beforeinterp, it must be totally
            # before the prior 24h time range. Set it to the OLDEST time
            # we have. (At this point currinterp will be 30h prior to earliest 
            # synoptic time). Doesn't really matter which one we pick, since all 
            # the prior 24h locations/speeds/etc are identical to the earliest 
            # track listed in the deck file.
            if not beforeinterp:
                beforeinterp = currinterp.copy()

        # Find the most recent name that is not empty.  
        if interp['stormname']:
            finalstormname = interp['stormname']

        # If actual_datetime is exactly the synoptic time, then we don't need to interpolate.
        # set before and after to synoptic_time
        if actual_datetime and interp['synoptic_time'] == actual_datetime:
            afterinterp = interp.copy()
            beforeinterp = interp.copy()
        # Keep loooooping through lines as long as the time of the line is BEFORE 
        # the ACTUAL date time (of the data). Store the last one as beforeinterp
        # In firsttime if statement above, we check all of the storm times 
        # that fall BEFORE the initial synoptic_time for the storm found in the 
        # deck file. 
        elif actual_datetime and interp['synoptic_time'] < actual_datetime:
            beforeinterp = interp.copy()
            continue
        # The next time through, store the line immediately following beforeinterp
        # as afterinterp
        elif actual_datetime and not afterinterp:
            afterinterp = interp.copy()
            continue
        # If actual_datetime is not passed (ie, process_overpass), just store all
        # of the lines in new_fields
        elif not actual_datetime:
            new_fields += [interp]
            continue
        # skip everything else.
        else:
            continue


    # We need to actually interpolate here!
    #
    # Probably want to use this to 1D interpolate lat/lon seperately:
    # http://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.InterpolatedUnivariateSpline.html
    #
    # Some example code that uses this functionality:
    # http://stackoverflow.com/questions/2745329/how-to-make-scipy-interpolate-give-an-extrapolated-result-beyond-the-input-range
    #
    # We may want to check for this kind of error in case there is not enough data to interpolate:
    # http://stackoverflow.com/questions/32230362/python-interpolate-univariatespline-package-error-mk-failed-for-hidden-m
    #

    # Here we should have the storm track line immediately before the actual
    # data time, and the storm track line immediately after.  There is a chance 
    # this will fall before the initial storm track line in the deck file - in that
    # case the code above should effectively set beforeinterp and afterinterp to the 
    # initial storm track line. So interp will end up just being the initial storm
    # location.
    if actual_datetime:
        # If we get through the entire file, we are now on the LATEST storm location,
        # and actual_datetime of the file is still GREATER than the latest storm 
        # location.  Meaning we never set afterinterp.  So just set afterinterp
        # to the latest storm location (interp).
        # This is only used if actual_datetime is set (for a real file).
        if not afterinterp:
            afterinterp = interp.copy()
        # For now, not interpolating, just taking the synoptic time before actual time
        # Interpolating will cause problems for ABI/AHI geolocation precalculation (since
        # a new storm location will require re-creating the geolocation variables, and we
        # currently rely on pre-calculating them as soon as we get a new storm location)
        interp = beforeinterp.copy()
        #interp['clat'] = (beforeinterp['clat'] + afterinterp['clat']) / 2
        #interp['clon'] = (beforeinterp['clon'] + afterinterp['clon']) / 2
        # This is not appropriate interpolation anyway, and it just makes 
        # TCs never match for dynamic geolocation. Going to have to rethink 
        # this whole thing to make it work with pre-generated geostationary
        # geolocation files.
        # Just comment it all out - keep beforeinterp altogether. I think the
        # time was making the pre-gen lat lon files not match.
        #interp['clat'] = beforeinterp['clat']
        #interp['clon'] = beforeinterp['clon']
        #interp['synoptic_time'] = actual_datetime
        # If actual_datetime is specified, new_fields will be valid at a single time.
        new_fields = [interp]

    sectors = []
    for fields in new_fields:
        sectors += [set_atcf_sector(fields,dynamic_templatefname, finalstormname, tcyear, sfname, dynamic_xmlpath)]

    return sectors

def parse_tc(line,dynamic_templatefname,sfname):

    dynamic_template_sf = geoips.sectorfile.open([dynamic_templatefname])
    sector = dynamic_template_sf.getsectors()[0]

    orig_sector = dynamic_template_sf.getsectors()[0]
    orig_sectorname = orig_sector.name

    try:
        try:
            (stormnum,stormname,date,time,clat,clon,basin,wind_speed,pressure) = line.split()
        # FNMOC sectorfile doesn't have pressure
        except ValueError:
            #log.exception('Did not pass 9 field space delimited '+str(resp))
            (stormnum,stormname,date,time,clat,clon,basin,wind_speed) = line.split()
            pressure=None

        basin = basin.upper()
        stormname = stormname.upper()
        year = int(date[:2]) 
        month = int(date[2:4])
        if year > 80:
            sector.dynamic_datetime=datetime.strptime('19'+date+'.'+time,'%Y%m%d.%H%M')
        else:
            sector.dynamic_datetime=datetime.strptime('20'+date+'.'+time,'%Y%m%d.%H%M')
        if orig_sectorname != '':
            newname = stormnum+stormname+'_'+orig_sectorname
        else:   
            newname = stormnum+stormname

    except (ValueError,AttributeError,IndexError):
        (basin,stormnum,YYYYMMDDHH,point,clat,clon,wind_speed,pressure) = line.split(',') 
        year = int(YYYYMMDDHH[:4]) 
        month = int(YYYYMMDDHH[4:6])
        stormname = str(year)+basin+stormnum
        stormnum = stormnum+basin
        if orig_sectorname != '':
            newname = stormname+'_'+orig_sectorname
        else:   
            newname = stormname
        sector.dynamic_datetime=datetime.strptime(YYYYMMDDHH,'%Y%m%d%H')

    '''November-June is the season for TCs in the southern hemisphere, 
    November/December storms must be counted in the following year's season'''
    if basin == "SH" or basin == "SHEM" and month > 6:
        year += 1

    
    stormnum= stormnum.replace('_','').replace('.','')
    stormname = stormname.replace('_','').replace('.','')
    newname = newname.replace('_','').replace('.','')
    sector.name = 'tc'+str(year)+newname

    sector.area_info.center_lat = clat
    sector.area_info.center_lon = clon

    sector.source_info.sourceflattextfile = sfname
    sector.source_info.sourcetemplate = dynamic_templatefname
    sector.source_info.sourceline = line.strip()
    # FNMOC sectorfile doesn't have pressure
    sector.tc_info.pressure = str(pressure)
    sector.tc_info.wind_speed = wind_speed
    sector.tc_info.clat = clat
    sector.tc_info.clon = clon
    sector.tc_info.dtg = sector.dynamic_datetime
    sector.tc_info.storm_num = stormnum
    sector.tc_info.storm_name = stormname

    sector.name_info.continent = "tc"+str(year)
    sector.name_info.country = 'x'
    sector.name_info.area = basin
    sector.name_info.subarea = stormnum+'.'+stormname
    log.debug('      Current TC sector: '+line.strip())

    return [sector]

def write_single_dynamic_xml_file(sector, force_update=False):
    # Need to make sure sourcedynamicxmlpath is not '', else try to write to /2016...   
    # But if sourcedynamicxmlpath is set and not empty, we want to use it.
    if hasattr(sector,'source_info') and hasattr(sector.source_info,'sourcedynamicxmlpath') and sector.source_info.sourcedynamicxmlpath:
        dynamic_sectorfilepath = os.path.expandvars(sector.source_info.sourcedynamicxmlpath)
    else:
        dynamic_sectorfilepath = plugins.paths['AUTOGEN_DYNAMIC_SECTORFILEPATH']

    sectors = [sector]
    YYYY = sector.dynamic_datetime.strftime('%Y')
    MMDD = sector.dynamic_datetime.strftime('%m%d')
    YYYYMMDD = sector.dynamic_datetime.strftime('%Y%m%d')
    HHMNSS= sector.dynamic_datetime.strftime('%H%M%S')
    curr_dyn_sfpath = dynamic_sectorfilepath+'/'+YYYY+'/'+MMDD
    #if os.path.exists(curr_dyn_sfpath) == False:
    #    log.debug('      %s does not exist. Creating now.' % curr_dyn_sfpath)
    #    os.makedirs(curr_dyn_sfpath,0775)
    # Lame, xml files link to ../sectorfiles.dtd... So linking it there.

    # Used to use genplot.filename MetaDataFileName - just build the filename directly, and use Path for makedirs...
    dynamic_sectorfile = Path(curr_dyn_sfpath+'/'+YYYYMMDD+'.'+HHMNSS+'.'+sector.name+'.'+sector.name_info.region+'.'+sector.name_info.subregion+'.xml')
    dynamic_sectorfile.makedirs()

    # This should be taken care of by xml_utilities when it doesn't find it?
    #link_dtd(dynamic_sectorfilepath+'/'+YYYY+'/sectorfiles.dtd')

    #log.debug('exists? '+dynamic_sectorfile.name)

    write_sector = True
    #print dynamic_sectorfile.name
    if os.path.exists(dynamic_sectorfile.name):
        #shell()
        # If you really want to replace the base path in the template with your own location - really just for testing
        # purposes.
        if os.getenv('GEOIPS_TEMPLATE_REPLACE') and os.getenv('GEOIPS_TEMPLATE_REPLACE_WITH') \
            and os.stat(dynamic_sectorfile.name).st_uid == os.getuid() \
            and os.getenv('GEOIPS_TEMPLATE_REPLACE_WITH') not in sector.source_info.sourcetemplate:
            dynamic_templatefname = \
                sector.source_info.sourcetemplate.replace(os.getenv('GEOIPS_TEMPLATE_REPLACE'),os.getenv('GEOIPS_TEMPLATE_REPLACE_WITH'))
        elif not os.path.exists(sector.source_info.sourcetemplate):
            bname = os.path.basename(sector.source_info.sourcetemplate)
            for tpath in plugins.paths['TEMPLATEPATHS']:
                if os.path.exists(tpath):
                    dynamic_templatefname = tpath+'/'+bname
            log.info('    sourcetemplate did not exist. REPLACING'+sector.source_info.sourcetemplate+' WITH '+dynamic_templatefname)
        else:
            dynamic_templatefname = sector.source_info.sourcetemplate
        dynamic_sf_timestamp = datetime.fromtimestamp(os.stat(dynamic_sectorfile.name).st_mtime)
        dynamic_template_timestamp = datetime.fromtimestamp(os.stat(dynamic_templatefname).st_mtime)
        log.info(str(dynamic_sf_timestamp)+' template: '+str(dynamic_template_timestamp)+' '+str(dynamic_templatefname))
        if dynamic_sf_timestamp < dynamic_template_timestamp:
            log.interactive('DYNAMIC SECTORFILE IS OUT OF DATE COMPARED WITH DYNAMIC TEMPLATE! Reproduce '+dynamic_sectorfile.name+' '+dynamic_templatefname)
            log.interactive('source line: '+sector.source_info.sourceline)
            log.interactive('dynamic_sf_timestamp: '+str(dynamic_sf_timestamp)+' dynamic_template_timestamp: '+str(dynamic_template_timestamp))
            sectors = parse_dynamic_entry(sector.source_info.sourceline,
                        dynamic_templatefname,
                        os.path.expandvars(sector.source_info.sourceflattextfile),
                        sector.dynamic_datetime)
        else:
            write_sector = False
    #print write_sector
    if force_update or write_sector:
        #log.debug('write_sector')
        for currsector in sectors:
            #print currsector.name
            #log.debug(' writing sector '+sector.name)
            YYYY = currsector.dynamic_datetime.strftime('%Y')
            MMDD = currsector.dynamic_datetime.strftime('%m%d')
            YYYYMMDD = currsector.dynamic_datetime.strftime('%Y%m%d')
            HHMNSS= currsector.dynamic_datetime.strftime('%H%M%S')
            curr_dyn_sfpath = dynamic_sectorfilepath+'/'+YYYY+'/'+MMDD

            # Used to use genplot.filename MetaDataFileName - just build the filename directly, and use Path for makedirs...
            curr_dynamic_sectorfile = Path(curr_dyn_sfpath+'/'+YYYYMMDD+'.'+HHMNSS+'.'+currsector.name+'.'+currsector.name_info.region+'.'+currsector.name_info.subregion+'.xml')
            curr_dynamic_sectorfile.makedirs()

            log.interactive('      Writing dynamic sector file: '+curr_dynamic_sectorfile.name)
            # MLS THIS IS WHERE \$DYNAMOC_SECTORFILEPATH IS HAPPENING!!!
            dsf = open(curr_dynamic_sectorfile.name,'w')

            dsf.write('<?xml version="1.0" standalone="no"?>\n')
            #dsf.write('<!DOCTYPE sector_file SYSTEM "sectorfiles.dtd">\n')
            #dsf.write('<sector_file>\n')
            #
            #dsf.write(str(sector))

            #dsf.write('\n</sector_file>')

            # FOR NOW YOU CAN ONLY HAVE A SINGLE SECTOR IN THE
            #   DYNAMIC SECTORFILE!!!!!!!! Need to fix this.
            #   It prints the entire root tree, so you get all
            #   of the other incomplete sectors as well as the
            #   one you are interested in.
            objectify.deannotate(currsector.node)
            dynamic_roottree = currsector.node.getroottree()
            dsf.write(etree.tostring(dynamic_roottree, pretty_print=True))

            dsf.close()


    return dynamic_sectorfile.name

def parse_dynamic_entry(line,dynamic_templatefname,sfname,actual_datetime=None):
    sectors = []
    log.info('Sector File Line: '+str(line))
    try:
        #log.info('    Trying TC...')
        sectors = parse_tc(line,dynamic_templatefname,sfname)
        #log.info('        MATCHED TC!!')
    except (ValueError,IndexError,AttributeError),resp:
        try:
            #log.info('        '+str(resp))
            #log.info('    Trying volcano...')
            sectors = parse_volcano(line,dynamic_templatefname,sfname)
            #log.info('        MATCHED VOLCANO!!')
        except (ValueError,IndexError,AttributeError),resp:
            try:
                #log.info('        '+str(resp))
                #log.info('    Trying PyroCB...')
                sectors = parse_pyrocb(line,dynamic_templatefname,sfname)
                #log.info('        MATCHED PYROCB!!')
            except:
                try:
                    #log.info('        '+str(resp))
                    #log.info('    Trying PyroCB...')
                    if actual_datetime:
                        sectors = parse_atcf_storm(sfname,actual_datetime)
                    #log.info('        MATCHED ATCF!!')
                except:
                    pass
                    #log.info('        '+str(resp))
                    #log.info('    All failed')
    return sectors

def get_emailaddress_from_line(line):
    # Take lower case of email address
    if '<' in line:
        emailaddress = re.sub('.*<','',line)
        emailaddress = re.sub('>.*','',emailaddress).strip().lower()
    else:
        emailaddress = line.replace('From:','').replace('Sender: ','').replace('Return-Path','').strip().lower()
    return emailaddress

def read_email_header(textsf):
    # Completely ignore any emails coming from addresses besides these. 
    if not os.getenv('DYNAMICEMAILVALID'):
        return None,False,False
    valid_emailaddresses = os.getenv('DYNAMICEMAILVALID').split(',')
    valid_emailsubjects = os.getenv('DYNAMICEMAILSUBJECTS').split(',')
    process_email = False
    send_response = False
    emailaddress = None
    log.info('Email message format - skipping header info....')
    for line in textsf:
    	log.info('Sector File Line: '+str(line))
        # Decide whether we are going to send a response or not.
        for valid_emailsubject in valid_emailsubjects:
            if re.match(valid_emailsubject,line):
                log.info('Subject '+valid_emailsubject+', will send an email response')
                process_email = True
                send_response = True
        if re.match('^Return-Path: ',line) or re.match('^Sender: ',line) or re.match('^From: ',line):
            # Default to Sender: address if it exists (From 
            # can be a forwarding address, use the actual address)
            if re.match('^From: ',line) and emailaddress:
                continue
            emailaddress = get_emailaddress_from_line(line)
            if '"' in emailaddress:
                emailaddress = get_emailaddress_from_line(next(textsf))
            if emailaddress not in valid_emailaddresses:
                log.info('Invalid email address, add to the list of allowed email addresses if needed.\n\t'+emailaddress.lower()+' not in '+str(valid_emailaddresses))
                return None,False,False

        line = line.strip()
        if line == '':
            return emailaddress,process_email,send_response

def draft_email_response(emailtxt,sectors,line):
    start_dt = {}
    end_dt = {}
    for sector in sectors:
        #log.info(sector.name)
        if sector.pyrocb_info:
            si = sector.pyrocb_info
        elif sector.tc_info:
            si = sector.tc_info
        elif sector.volcano_info:
            si = sector.volcano_info
        if sector.name not in start_dt.keys() or sector.dynamic_datetime < start_dt[sector.name]:
            start_dt[sector.name] = sector.dynamic_datetime
        if sector.name not in end_dt.keys() or sector.dynamic_endtime > end_dt[sector.name]:
            end_dt[sector.name] = sector.dynamic_endtime
        emailtxt[sector.name] = '    Lat: '+si.minlat+' to '+si.maxlat+\
                '\n    Lon: '+si.minlon+' to '+si.maxlon+\
                '\n    Active period: '+start_dt[sector.name].strftime('%Y%m%d.%H%M%S')+\
                ' to '+end_dt[sector.name].strftime('%Y%m%d.%H%M%S')+\
                '\n    Original Line: '+line
    return emailtxt

def send_email_response(emailaddress,emailtxt,bodylines):
    if not os.getenv('DYNAMICEMAILREPLYTO'):
        log.info('DYNAMICEMAILREPLYTO not set, not sending email response')
        return None
    fromemail = str(os.getenv('DYNAMICEMAILREPLYTO'))
    if emailtxt:
        finalemailtxt = ['Thank you for submitting a dynamic sector request.\n'+
            'Please contact '+fromemail+
            ' if products do not appear, or '+
            'if the sector parameters listed below are not correct:\n']
        for sectorname in emailtxt.keys():
            finalemailtxt += ['Sector Name: '+sectorname+'\n'+emailtxt[sectorname]]
    else:
        finalemailtxt = ['The dynamic sector request you previously sent was improperly formatted.\n\n'+
                'Please try again with appropriate formatting']
    msg = MIMEText('\n'.join(finalemailtxt))
    msg['Subject'] = 'GeoIPS Dynamic Sector Creation'
    msg['From'] = fromemail
    msg['To'] = emailaddress

    s = smtplib.SMTP('localhost')
    log.info('Emailing response: \n'+msg.as_string())
    s.sendmail(fromemail, [emailaddress], msg.as_string())
    s.quit()

def write_dynamic_xml_files(dynamic_templatefname,sfname,return_sectornames=False):

    badentries = []
    dynamic_sectorfilenames = []

    num_good = 0
    num_bad = 0

    textsf = open(sfname,'r') 

    log.info('    Reading dynamic sectors from '+sfname)

    # For determining email parameters
    emailtxt = {}
    emailaddress = None
    process_email = False
    send_response = False
    bodylines = []
    sectornames = []

    for line in textsf:
        line = line.strip()
        #log.info(line)

        # If one of these fields is found in the first 5 lines, we determine it is an email file.
        # Read the headers, then we should be left with the body.
        if 'Return-Path: ' in line or 'X-Original-To: ' in line or 'Delivered-To: ' in line:
            emailaddress,process_email,send_response = read_email_header(textsf)


        # There may be more than 5 bad lines in the body area of the email, so 
        # do not cut off after 5 bad lines if we are dealing with an email file.
        if not emailaddress and num_good == 0 and num_bad > 5:
            log.debug('      First 5 don\'t match TC format or volcano or pyrocb format, assuming not TC or volcano or pyrocb file... moving on!!')
            textsf.close()
            return dynamic_sectorfilenames

        # If emailaddress is defined, that means it is an email file. 
        # process_email will be set on valid email file in read_email_header
        # if it is an email type we want processed (right now only pyrocbs)
        if emailaddress:
            if process_email:
                bodylines += [line]
            # If it was a valid email address, but we do not want to process it, 
            # break out of the loop.
            else:
                break

        try:
            sectors = parse_dynamic_entry(line,dynamic_templatefname,sfname)
            for sector in sectors:
                #log.info(sector.name)
                if sector.name not in sectornames:
                    sectornames.append(sector.name)
                dynamic_sectorfilenames.append(write_single_dynamic_xml_file(sector))
                num_good += 1
            if emailaddress:
                emailtxt = draft_email_response(emailtxt,sectors,line)
        except (ValueError,IndexError,AttributeError),resp:
            num_bad += 1
            log.debug(str(resp)+': Invalid flattext sector file entry, skipping line')
            badentries.append(str(resp)+': Invalid flattext sector file entry, skipping line')


    if emailaddress and send_response:
        send_email_response(emailaddress,emailtxt,bodylines)

    if dynamic_sectorfilenames != [] and badentries != []:
        log.warning('\n      '.join(badentries))

    textsf.close()

    if return_sectornames:
        return sectornames
    else:
        return dynamic_sectorfilenames
    
def create_dynamic_xml_sectorfiles_from_deckfile(atcf_deck_filename,actual_datetime=None, force_update=False):
    dynamic_sectorfilenames = []
    try:
        log.info('Checking '+atcf_deck_filename)
        sectors = parse_atcf_storm(atcf_deck_filename,actual_datetime)
    except Exception,resp:
        log.exception(str(resp)+'   Invalid file, SKIPPING atcf deck file '+str(atcf_deck_filename)+'!!! Giving up and moving onto the next one'+commands.getoutput('ls --full-time '+str(atcf_deck_filename))+commands.getoutput('cat '+str(atcf_deck_filename)))

    for sector in sectors:
        dynamic_sectorfilenames.append(write_single_dynamic_xml_file(sector,force_update=force_update))

    return dynamic_sectorfilenames

def create_dynamic_xml_sectorfiles_from_db(start_datetime,end_datetime,actual_datetime=None, force_update=False):

    dynamic_sectorfilenames = []
    atcf_deck_filenames = get_timerange_from_db(start_datetime,end_datetime)
    for atcf_deck_filename in atcf_deck_filenames:
        dynamic_sectorfilenames += create_dynamic_xml_sectorfiles_from_deckfile(atcf_deck_filename[1],actual_datetime=actual_datetime,force_update=force_update)

    return dynamic_sectorfilenames

def create_dynamic_xml_sectorfiles(str_dynamic_templatefiles,sectorfilenames,start_datetime,end_datetime,actual_datetime=None):

    '''This creates individual dynamic xml sectorfiles. These final xml files are 
        complete and usable directly in the Processing System.
        
        1) Checks for existence of sectorfiles.dtd in the Dynamic XML Sectorfile 
            Path - this is where the final, usable xml files will reside. If 
            sectorfiles.dtd does not exist, it is LINKED from the static 
            xml sectorfile path.
        1) Reads all dynamic template xml files - these files are incomplete 
            xml files 
        2) Goes through all 
    '''

    dynamic_sectorfilenames = []
    dynamic_sectorfilenames += create_dynamic_xml_sectorfiles_from_db(start_datetime, end_datetime, actual_datetime)


    dynpath = plugins.paths['AUTOGEN_DYNAMIC_SECTORFILEPATH']
    log.debug('Writing dynamic sectorfiles to '+dynpath)
    # MUST HAVE / ON END OR IT WON'T WORK!
    pathobj = Path(dynpath+'/')
    pathobj.makedirs()

    # This should be taken care of by xml_utilities when it doesn't find it?
    #link_dtd(dynpath+'/../sectorfiles.dtd')
    #link_dtd(dynpath+'/sectorfiles.dtd')


    if sectorfilenames == None:
        sectorfilenames = []
    sfnames = sectorfilenames
#    for sfname in sectorfilenames:
#        try:
#            # Try opening sfname, if it is a valid Sectorfile object, then 
#            # we will not bother with trying to parse it as a flattext 
#            # sectorfile
#            log.debug('Trying to open '+sfname)
#            sf = geoips.sectorfile.open([sfname])
#        except KeyError:
#            log.debug('    open failed, adding'+sfname)
#            sfnames.append(sfname)
#            continue

    for dynamic_templatefname in str_dynamic_templatefiles:
        log.info(dynamic_templatefname)
        dynamic_template_sf = geoips.sectorfile.open([dynamic_templatefname])
        orig_sector = dynamic_template_sf.getsectors()[0]
        curr_sfnames = sfnames
        if sfnames == []:
            if orig_sector.tc_info != None or orig_sector.volcano_info != None or orig_sector.pyrocb_info != None:
                curr_sfnames = [os.path.expandvars(orig_sector.source_info.sourceflattextfile)]
        
        for sfname in curr_sfnames:
            if os.path.exists(sfname):
                dynamic_sectorfilenames.extend(write_dynamic_xml_files(dynamic_templatefname,sfname))

    #            add_to_db(sector)


    return dynamic_sectorfilenames

    
