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
import shutil
import re
from datetime import datetime


# Installed Libraries
try:
    # Don't fail if this doesn't exist
    from IPython import embed as shell
except:
    print 'Failed IPython import in driver.py. If you need it, install it.'
    
#from pyorbital import orbital
import ephem


# GeoIPS Libraries
#from satellite_info import tle_names,tscan_names
from geoips.utils.satellite_info import all_available_satellites,get_celestrak_tle_name,get_tscan_tle_name
from geoips.utils.plugin_paths import paths as gpaths


pull_celestrak = True 
use_terascan = False

# TLE directory that we actually use
desttlepath = gpaths['SATOPS']+'/longterm_files/tle'

# If TLEs are automatically pushed to the system, this is 
# the directory they are pushed to (None, or same as desttlepath
# if not needed)
sourcetlepath = None
if os.getenv('SOURCE_TLE_DIR'):
    sourcetlepath = os.getenv('SOURCE_TLE_DIR')
    # Meaning someone else is pulling them for us so we don't.
    pull_celestrak = False

# Where we look for terascan files to convert to our needed
# tle input.  Just no-ops if it doesn't exist.
tscan_tlepath = None
if os.getenv('SOURCE_TSCANTLE_DIR'):
    tscan_tlepath = os.getenv('SOURCE_TSCANTLE_DIR')
    use_terascan = True

if not os.path.exists(desttlepath):
    os.makedirs(desttlepath)

print 'dest tlepath: '+desttlepath
print 'source tlepath: '+str(sourcetlepath)
print 'tscan tlepath: '+str(tscan_tlepath)
print 'pull_celestrak: '+str(pull_celestrak)
print 'use_terascan: '+str(use_terascan)
print ''

def exists_in_tle_file(newtleline1,oldtleobj):
    for line in oldtleobj:
        if newtleline1.strip() == line.strip():
            #print "1START"+newtleline1.strip()+"END"
            #print "2START"+line.strip()+"END"
            #print "MATCHED!"
            return True
    return False

def write_to_tle_file(newtlefile,tlelines):

    #print tlelines
    try:
        tle = ephem.readtle(tlelines[0],tlelines[1],tlelines[2])
        tle.compute()

        # pyorbital gave us the date based on TLE when opening a TLE
        # for some reason ephem doesn't store that. So parsing it myself..
        # actually only need YYJJJ, only use for setting directory/file name...
        newdtstr = tlelines[1].split()[3]
        YYJJJ,PH = newdtstr.split('.')
        PH = float('.'+PH)*24
        HH,PM = divmod(PH,1)
        HH = '{:02.0f}'.format(HH)
        PM *= 60
        MN,PS = divmod(PM,1)
        MN = '{:02.0f}'.format(MN)
        PS *= 60
        SS = int(PS)
        SS = '{:02.0f}'.format(SS)
        newdt = datetime.strptime(YYJJJ+HH+MN+SS,'%y%j%H%M%S')
    except ValueError:
        return None

    #print "Checking overpass time: "+str(newdt)+' for '+tlelines[0].strip()

    newtle = desttlepath+'/'+newdt.strftime('%Y/%m/%d')
    if not os.path.exists(os.path.dirname(newtle)):
        os.makedirs(os.path.dirname(newtle))
    tleobj = open(newtle,'a+')
    # Just check line '1' for existence in file, contains date, etc
    #print "Checking file: "+newtle
    if not exists_in_tle_file(tlelines[1],tleobj):
        for tleline in tlelines:
            print(newtle+': '+tleline.strip())
            tleobj.write(tleline)
    tleobj.close()
    return newtle

def cleanup_celestrak_file(celestrak_file):
    cf = open(celestrak_file,'r')
    clean = open(celestrak_file+'clean','w')
    for line in cf:
        clean.write(re.sub('\[.*','',line).strip()+'\n')
    return celestrak_file+'clean'

if (use_terascan):
    print ''
    print ''
    print 'Using tscan_tlepath '+tscan_tlepath
    print ''

    #for gisat,tlesat in tle_names.iteritems():
    for gisat in all_available_satellites():
        badlines = 0
        goodlines = 0
        tscan_tle_name = get_tscan_tle_name(gisat)
        celestrak_tle_name = get_celestrak_tle_name(gisat)
        # This will be undefined if it is not low orbit (no TLEs for geo)
        # Also undefined for satellites tscan does not track - ie ISS
        if not celestrak_tle_name or not tscan_tle_name:
            continue
        tscan_tlefile = tscan_tlepath+'/'+tscan_tle_name+'/twoinput'
        if not os.path.exists(tscan_tlefile):
            print('    No tscan tle for '+gisat+'!')
            continue
        print('cp -p '+tscan_tlefile+' '+desttlepath+'/ts_'+gisat+'.txt')
        os.system('cp -p '+tscan_tlefile+' '+desttlepath+'/ts_'+gisat+'.txt')
        tstwoinput = open(desttlepath+'/ts_'+gisat+'.txt')
        dt = None
        tlelines = []
        for line in tstwoinput:
            parts = line.split()
            if parts[0] == '1':
                try:
                    [YYJJJ,fracday] = parts[3].split('.')
                except ValueError:
                    [YYJJJ,fracday] = parts[4].split('.')
                dt = datetime.strptime(YYJJJ,'%y%j')
                tlelines = [celestrak_tle_name+'\n',line]
            if parts[0] == '2':
                if not write_to_tle_file(dt,tlelines+[line]):
                    badlines += 1
                else:
                    goodlines += 1
        print('    '+str(badlines)+' bad lines in file')
        print('    '+str(goodlines)+' good lines in file\n')



if pull_celestrak:
    print ''
    print ''
    print 'Pulling celestrak tles to desttlepath '+desttlepath
    print ''
    # MLS 20160223 add -t 2 so it will only try twice instead of 20 times if we accidentally leave
    #     get_remote on on a system that can't actually pull...
    print("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/weather.txt -P "+desttlepath)
    os.system("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/weather.txt -P "+desttlepath)
    print("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/stations.txt -P "+desttlepath)
    os.system("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/stations.txt -P "+desttlepath)
    print("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/resource.txt -P "+desttlepath)
    os.system("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/resource.txt -P "+desttlepath)
    print("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/noaa.txt -P "+desttlepath)
    os.system("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/noaa.txt -P "+desttlepath)
    print("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/science.txt -P "+desttlepath)
    os.system("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/science.txt -P "+desttlepath)
    print("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/sbas.txt -P "+desttlepath)
    os.system("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/sbas.txt -P "+desttlepath)
    print("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/geo.txt -P "+desttlepath)
    os.system("wget --timestamping -t 2 http://celestrak.com/NORAD/elements/geo.txt -P "+desttlepath)

if sourcetlepath and desttlepath != sourcetlepath:
    print ''
    print ''
    print 'Copying tles from sourcetlepath to desttlepath '+desttlepath
    print ''
    # If a system has an automatic push of TLEs, just copy them to 
    # the desttlepath for use (probably want to keep the push directory
    # clean)
    for tlefilename in ['weather.txt','stations.txt','resource.txt',
                        'noaa.txt','science.txt','sbas.txt','geo.txt']:
        tlefile = sourcetlepath+'/'+tlefilename
        if os.path.exists(tlefile):
            print '    Copying '+tlefile+' to desttlepath'
            shutil.copy2(tlefile,desttlepath)


print ''
print ''
print 'Rearranging Celestrak TLEs into desttlepath '+desttlepath
print ''
for tlefile in ['weather.txt','stations.txt','resource.txt','noaa.txt','science.txt','sbas.txt','geo.txt']:
    badlines = 0
    goodlines = 0
    if not os.path.exists(desttlepath+'/'+tlefile):
        print('TLEFILE '+desttlepath+'/'+tlefile+' DOES NOT EXIST!!! Skipping')
        continue
    print('    Checking for new locations in TLE file '+tlefile+' ... ')
    newtlefile = cleanup_celestrak_file(desttlepath+'/'+tlefile)
    newtlefileobj = open(newtlefile,'r')
    for sat in newtlefileobj:
        sat = sat.strip()
        try:
            if sat[0] == '1' or sat[0] == '2':
                continue
        # If it does not appear to be a TLE file at all, skip it...
        except IndexError,resp:
            continue
        for gisat in all_available_satellites():
            #print sat+' '+gisat
            celestrak_tle_name = get_celestrak_tle_name(gisat)
            if sat == celestrak_tle_name:
                line1 = newtlefileobj.next().strip()
                line2 = newtlefileobj.next().strip()
                if not write_to_tle_file(newtlefile,[celestrak_tle_name+'\n',line1+'\n',line2+'\n']):
                    badlines += 1
                else:
                    goodlines += 1
    print('      '+str(badlines)+' bad lines in file')
    print('      '+str(goodlines)+' good lines in file\n')

