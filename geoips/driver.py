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
import gc
import os
import logging
import socket
from datetime import timedelta, datetime
import multiprocessing

# Installed Libraries
try:
    # Don't fail if this doesn't exist (not even used at the moment)
    from memory_profiler import profile
except:
    print 'Failed memory_profiler import in driver.py. If you need it, install it.'
try:
    # Don't fail if this doesn't exist (only needed for specific readers)
    import netCDF4  # This must be imported before h5py, which is imported in SciFile
except:
    print 'Failed netCDF4 import in driver.py. If you need it, install it.'
try:
    # Don't fail if this doesn't exist (only needed for specific readers)
    import h5py  # This must be imported before lxml, which is imported in process ?
except:
    print 'Failed h5py import in driver.py. If you need it, install it.'
import matplotlib 
matplotlib.use('agg') # Believe this must be set before something else is imported? So do it up front

# GeoIPS Libraries
from geoips.process import process
import geoips.sectorfile as sectorfile
import geoips.productfile as productfile
from geoips.scifile import SciFile
from geoips.utils.main_setup import ArgParse  # , uncaught_exception
from geoips.utils.log_setup import interactive_log_setup, root_log_setup
from geoips.utils.path.filename import _FileNameBase
from geoips.utils.memusg import print_mem_usage
from geoips.pass_prediction.pass_prediction import pass_prediction
from geoips.utils.plugin_paths import paths as gpaths


SHAREDSCRATCH = os.getenv('SHAREDSCRATCH')
LOCALSCRATCH = os.getenv('LOCALSCRATCH')
MAXCPUS = os.getenv('MAXCPUS')
GEOIPS_OPERATIONAL_USER = os.getenv('GEOIPS_OPERATIONAL_USER')
EMAIL_SUBJECT = 'GIWrapper'

# Set up logger
log = interactive_log_setup(logging.getLogger(__name__))
bigindent = '\n{0}'.format(' ' * 40)

# Global variables
SUBPROCS = {}  # Container for any spawned processes
DATETIMES = {}
CLEANUP_FILES = []

__all__ = ['driver']

__doc__ = '''
          ``driver`` is called to produce imagery from a single data file.
          The routine can either be called at command line in order to produce
          imagery from a single data file or can be called by higher level scripts
          in order to produce imagery from more than one data file.
          For example, ``driver`` is called from :doc:`process_overpass <process_overpass>` and
          the various :doc:`downloaders <downloaders>`.

          ``driver`` performs multiple functions in the processing stream including:

          - read sectorfiles
          - check coverage of input data with each sector
          - sectors data to remove any unnecessary data. Needs work in the case where no orbital elements exist.
          - calls :doc:`gisector <gisector>` once per sector

          '''


# MLS 20160203 monitor - mem jump at process() call
#  Pulled the bulk of processing out of driver so we can more easily run
#    memory_profiler on it. Please forgive the huge argument list...
#  Don't profile this when doing multiprocessing (polling loop makes a
#    lot of output...)
# @profile
def run_sectors(data_file, sector_file, productlist, sectorlist, forcereprocess, no_multiproc, mp_max_cpus,
                printmemusg, sects, mp_jobs, mp_waiting, geoips_only, sectors_run, mp_num_procs,
                mp_max_num_jobs, mp_num_waits, mp_num_times_cleared, waittimes, didmem, separate_datasets,
                write_sectored_datafile, write_registered_datafile):
    if printmemusg and (datetime.utcnow().second % 5) == 0 and not didmem:
        print_mem_usage('drmainloop ', printmemusg)
        didmem = True
    elif printmemusg and (datetime.utcnow().second % 5) != 0 and didmem:
        didmem = False

    # pass max num cpus as option to ddriver.py. default to 1.
    if sects and len(mp_jobs) < int(mp_max_cpus):
        curr_sector = sects.pop()
        try:
            earthradius = 6371.0
            ad = curr_sector.area_definition
            ai = curr_sector.area_info
            log.info('Sector information:')
            log.info('\tNAME:\t{0}'.format(curr_sector.name))
            log.info('\tAREA:\t{0}km^2'.format(ad.get_area() * earthradius**2))
            log.info('\tX SIZE:\t{0} pixels'.format(ad.x_size))
            log.info('\tY SIZE:\t{0} pixels'.format(ad.y_size))
            # log.info('\tCALC X SIZE:\t{0}'.format(curr_sector.area_info.num_samples_calc))
            # log.info('\tCALC Y SIZE:\t{0}'.format(curr_sector.area_info.num_lines_calc))
            log.info('\tWIDTH:\t{0}km'.format(ai.width / 1000.0))
            log.info('\tHEIGHT:\t{0}km'.format(ai.height / 1000.0))
            log.info('\tPIXEL WIDTH:\t{0}km'.format(ad.pixel_size_x / 1000.0))
            log.info('\tPIXEL HEIGHT:\t{0}km'.format(ad.pixel_size_y / 1000.0))
            log.info('\tMIN/MAX LAT:\t{0} - {1}'.format(ai.min_lat_float, ai.max_lat_float))
            log.info('\tMIN/MAX LON:\t{0} - {1}'.format(ai.min_lon_float, ai.max_lon_float))
            log.info('\tCENTER LAT:\t{0}'.format(ai.center_lat_float))
            log.info('\tCENTER LON:\t{0}'.format(ai.center_lon_float))
            log.info('\tCORNERS:\t{0}'.format(curr_sector.area_definition.corners))
        # Unsure why there is a try/except here.  Test this.
        except ValueError, resp:
            log.info('\tAREA:\tUnknown km^2')

        plog = 'dr{0} '.format(curr_sector.name)

        DATETIMES['start_{0}'.format(curr_sector.name)] = datetime.utcnow()
        log.info('\n\n')
        print_mem_usage('{0} start of sector {1} mp_max_cpus = {2}, mp_jobs = {3}'.format(
            plog, curr_sector.name, mp_max_cpus, mp_jobs))

        # THIS MAY NOT BE NEEDED!  Putting in for now
        # If a sector is set to active='no', skip it
        if curr_sector.isactive is False:
            log.interactive('{0} {1} sector is not active.  Skipping...'.
                            format(plog, curr_sector.name))
            ret = mp_num_waits, mp_num_procs, mp_num_times_cleared,\
                mp_max_num_jobs, mp_waiting, didmem
            return ret
        # Allow for leaving sectors on interactively, but off operationally
        elif GEOIPS_OPERATIONAL_USER and not curr_sector.isoperational:
            log.interactive('{0} {1} sector is not operational.  Skipping...'.
                            format(plog, curr_sector.name))
            ret = mp_num_waits, mp_num_procs, mp_num_times_cleared,\
                mp_max_num_jobs, mp_waiting, didmem
            return ret

        # At this point, we have found an active sector in our sectorfile
        log.interactive('{0} NEXT Testing {1} sector from file {2}.'.format(
            plog, curr_sector.name, curr_sector.sourcefile))
        log.interactive('{0} sectors left; {1} sectors completed.'.format(len(sects), len(sectors_run)))
        log.interactive('{0} MP Jobs; {1} CPUS'.format(len(mp_jobs), mp_max_cpus))

        if sectorlist and curr_sector.name.lower() not in sectorlist:
            log.interactive('{0}    NOT REQUESTED.'.format(plog))
            ret = mp_num_waits, mp_num_procs, mp_num_times_cleared, mp_max_num_jobs, mp_waiting, didmem
            return ret

        # Test to be sure sector requires data from data_file's source, or source_name special ALLSOURCES
        if not curr_sector.run_on_source(data_file.source_name):
            log.interactive('{0} {1} data is not required for {2}, add it to sectorfile if desired'.format(
                            plog, data_file.source_name, curr_sector.name))
            ret = mp_num_waits, mp_num_procs, mp_num_times_cleared, mp_max_num_jobs, mp_waiting, didmem
            return ret

        # Get products needed based on passed productlist and current source
        curr_productlist = curr_sector.get_requested_products(data_file.source_name, productlist)

        if not curr_productlist:
            log.interactive('{0} SKIPPING: No requested products available for sector'.format(plog))
            ret = mp_num_waits, mp_num_procs, mp_num_times_cleared, mp_max_num_jobs, mp_waiting, didmem
            return ret

        # Determine which variables need to be read
        log.interactive('{0} Using variables from products: {1}'.format(plog, curr_productlist))
        try:
            required_vars = curr_sector.get_required_vars(data_file.source_name, curr_productlist)
            required_vars += curr_sector.get_optional_vars(data_file.source_name, curr_productlist)
        # This portion needs to be rethought.  Currently will skip an entire sector any time a single product file
        #   is missing.  Correct behavior would be to remove the offending product from the product list.
        except productfile.ProductFileError.ProductFileError, resp:
            log.warning('{0}    Product files "{1}" do not exist, skipping'.format(
                log, ' '.join(curr_productlist)))
            ret = mp_num_waits, mp_num_procs, mp_num_times_cleared, mp_max_num_jobs, mp_waiting, didmem
            return ret

        # If it is 'SECTOR_ON_READ' type reader, we won't have any variables because we haven't read yet...
        if ('SECTOR_ON_READ' not in data_file.metadata['top'].keys() or not data_file.metadata['top']['SECTOR_ON_READ']) \
            and not data_file.has_any_vars(required_vars):
            log.interactive('{0} No channels available, skipping current sector'.format(plog))
            ret = mp_num_waits, mp_num_procs, mp_num_times_cleared, mp_max_num_jobs, mp_waiting, didmem
            return ret

        log.interactive('{0} Sectoring data.'.format(plog))
        sectored = None

        if 'SECTOR_ON_READ' in data_file.metadata['top'].keys() and data_file.metadata['top']['SECTOR_ON_READ']:
            # Readers that sector at read time must set df.metadata['top']['SECTOR_ON_READ'].
            # These need to be re-read for each sector.
            log.info('    SECTOR_ON_READ set on data_file, reading data for sector: '.format(curr_sector.name))
            sectored = SciFile()
            # Read the next sector_definition
            sectored.import_data(runpaths, chans=chans, sector_definition=curr_sector)
        elif 'NON_SECTORABLE' in data_file.metadata['top'].keys() and data_file.metadata['top']['NON_SECTORABLE']:
            # Readers that are not able to be sectored  must set df.metadata['top']['NON_SECTORABLE'].
            # Driver will then skip attempting to sector
            log.info('    NON_SECTORABLE set on data_file, not attempting to sector data for sector: '+curr_sector.name)
            sectored = data_file
        else:
            try:
                print_mem_usage('{0} before sectoring data'.format(plog, curr_sector.name))
                sectored = data_file.sector(curr_sector.area_definition, required_vars)
                print_mem_usage('{0} after sectoring data'.format(plog, curr_sector.name))
                if not sectored or not sectored.datasets.keys():
                    log.interactive('    {0} Skipping current sector {1}, no coverage'.format(
                        plog, curr_sector.name))
                    ret = mp_num_waits, mp_num_procs, mp_num_times_cleared, mp_max_num_jobs, mp_waiting, didmem
                    return ret
                # log.info('sectored dataprovider: '+str(sectored.dataprovider))
            except Exception, resp:
                # log.interactive(plog+str(resp)+' Skipping current sector')
                log.exception('{0} {1} Sectoring failed!! Skipping...'.format(resp, plog))
                ret = mp_num_waits, mp_num_procs, mp_num_times_cleared, mp_max_num_jobs, mp_waiting, didmem
                return ret

        if not sectored or not sectored.datasets.keys() or data_file.source_name in ['gvar']:
            if data_file.source_name in ['gvar']:
                covg = False
                try:
                    for dsname in data_file.datasets.keys():
                        log.info('    Checking coverage for dataset {0} with overlaps_minmaxlatlon'.format(dsname))
                        data_corners = data_file.datasets[dsname].data_box_definition.corners
                        sect_corners = curr_sector.area_definition.corners
                        log.info('        Data corners: {0}'.format(data_corners))
                        log.info('        Sector corners: {1}'.format(sect_corners))
                        if not covg and data_file.datasets[dsname].data_box_definition.overlaps_minmaxlatlon(
                                curr_sector.area_definition):
                            log.warning(('    {0} Running without sectoring! Geo data appears ' +
                                         'to have coverage, but can\'t actually sector yet').format(plog))
                            sectored = data_file
                            covg = True
                except Exception, resp:
                    log.exception('{0} {1} Coverage check failed, still running without sectoring'.format(
                        resp, plog))
                    sectored = data_file
                    covg = True
                if not covg:
                    log.info(('    {0} Skipping current sector {1}, no coverage ' +
                             'using overlaps_minmaxlatlon'.format(plog, curr_sector.name())))
                    return mp_num_waits, mp_num_procs, mp_num_times_cleared, mp_max_num_jobs, mp_waiting, didmem
            else:
                log.interactive(('    {0} Skipping current sector {1}, ' +
                                 'no coverage'.format(plog, curr_sector.name)))
                return mp_num_waits, mp_num_procs, mp_num_times_cleared, mp_max_num_jobs, mp_waiting, didmem

        #notes = 
        '''
         MLS This is a good place to enter iPython in order to interrogate
               the SECTORED data file for development purposes.

           sectored.datasets.keys()
           sectored.datasets[<dsname>].variables.keys()
           sectored.datasets[<dsname>].variables[<varname>].min()
           sectored.datasets[<dsname>].variables[<varname>].max()

           geolocation_variables must be named 'Latitude' and 'Longitude'
           sectored.datasets[<dsname>].geolocation_variables['Latitude']
           sectored.datasets[<dsname>].geolocation_variables['Longitude']

           metadata is set in the readers - any arbitrary metadata field
           can be set in the reader, but scifile only absolutely requires 
           'start_datetime' 'source_name' and 'platform_name'
           All other fields can be accessed throughout the processing, 
           but are not required internally to scifile

           metadata at the top scifile level, _finfo fields pulled from metadata['top']:
           sectored.metadata['top']
           sectored._finfo

           metadata at the dataset level, _dsinfo fields pulled from metadata['ds']:
           sectored.metadata['ds']
           sectored.datasets[<dsname>]._dsinfo

           metadata at the variable level, _varinfo fields pulled from metadata['datavars']:
           sectored.metadata['datavars']
           sectored.datasets[<dsname>].variables[<varname>]._varinfo

           metadata at the geolocation_variable level, _varinfo fields pulled from metadata['gvars']:
           sectored.metadata['datavars']
           sectored.datasets[<dsname>].variables[<varname>]._varinfo

           sectored.source_name, sectored.platform_name, sectored.start_datetime, etc pulled directly
           from the ._*info dictionaries (which were originally specified in the metadata dictionary

           At some point I want to rename 
           'ds' to 'datasets', 
           'datavars' to 'variables'
           'gvars' to 'geolocation_variables' 
           in the metadata dictionary, but we'll have to change a bunch of readers first.
        '''
        #print notes
        #from IPython import embed as shell
        #shell()

        '''If user requested write_sectored_datafile command line, then see if this is not
            already a PRESECTORED data file, and write if necessary
        '''
        if write_sectored_datafile:
            write_file = False
            '''Currently we will not rewrite if all datafiles are already
                in PRESECTORED_DATA_PATH (meaning it was already written out)
            '''
            for dfname in sectored.datafiles.keys():
                if gpaths['PRESECTORED_DATA_PATH'] not in dfname:
                    write_file = True
            if write_file:
                from geoips.scifile.utils import write_datafile
                '''Currently only h5 is supported.  Will have to write new def write for additional
                    filetypes
                   write_datafile determines appropriate paths and filename based
                    on all the datasets contained in the scifile object.
                '''
                log.info('Attempting to write out data file to  %s' % (gpaths['PRESECTORED_DATA_PATH']))
                write_datafile(gpaths['PRESECTORED_DATA_PATH'],sectored,curr_sector, filetype='h5')
        if write_registered_datafile:
            write_file = False
            ''' Currently we will NOT rewrite if all datafiles are already in
                PREREGISTERED_DATA_PATH (meaning it was already written out)'''
            for dfname in sectored.datafiles.keys():
                if gpaths['PREREGISTERED_DATA_PATH'] not in dfname:
                    write_file = True
            if write_file:
                from geoips.scifile.utils import write_datafile
                ''' Currently only h5 is supported.  Will have to write new def 
                    write for additional filetypes
                    write_datafile determines appropriate paths and filenames
                    based on all the datasets contained in the scifile object
                '''
                log.info('Attempting to register datafile')
                sectored = sectored.register(curr_sector.area_definition)
                log.info('Attempting to write out data file to %s' % (gpaths['PREREGISTERED_DATA_PATH']))
                write_datafile(gpaths['PREREGISTERED_DATA_PATH'], sectored, curr_sector, filetype='h5')

        log.info('{0} Checking products'.format(plog))

        # This is for timing the running of different sections of driver.py
        DATETIMES['startallproc_{0}'.format(curr_sector.name)] = datetime.utcnow()

        if mp_waiting:
            # This is purely for log purposes
            DATETIMES['end_wait_time{0}'.format(mp_num_waits)] = datetime.utcnow()
            end_wait_time = DATETIMES['end_wait_time{0}'.format(mp_num_waits)]
            start_wait_time = DATETIMES['start_wait_time{0}'.format(mp_num_waits)]
            waittimes[mp_num_waits] = end_wait_time - start_wait_time
            log.info('{0} MPLOG Waited for {1}'.format(plog, (waittimes[mp_num_waits])))
            mp_waiting = False
        if no_multiproc:
            log.info('{0} NOT USING MULTIPROCESSING'.format(plog))
            orig_shape = [dsvars.shape for dss in data_file.datasets.values() for dsvars in
                          dss.variables.values()]
            sectored_shape = [dsvars.shape for dss in sectored.datasets.values() for dsvars in
                              dss.variables.values()]
            log.info('Original data shape: {0}'.format(orig_shape))
            log.info('Sectored data shape: {0}'.format(sectored_shape))
            # utils.path.productfilename needs sector_file for calling pass_prediction
            # Pass rather than opening again.
            if separate_datasets:
                dfnew = SciFile()
                log.info('Running each dataset separately through process')
                dfnew.metadata = sectored.metadata.copy()
                olddsname = None
                for dsname in sectored.datasets.keys():
                    if olddsname:
                        dfnew.delete_dataset(olddsname)
                    dfnew.add_dataset(sectored.datasets[dsname])
                    if 'datasets' in dfnew.metadata and dsname in dfnew.metadata['datasets'].keys():
                        for key in dfnew._finfo.keys():
                            if key in dfnew.metadata['datasets'][dsname].keys():
                                dfnew.metadata['top'][key] = dfnew.metadata['datasets'][dsname]['platform_name']
                                dfnew.datasets[dsname].platform_name = dfnew.metadata['top']['platform_name']
                    olddsname = dsname
                    process(dfnew, curr_sector, productlist, forcereprocess=forcereprocess,
                        sectorfile=sector_file, printmemusg=printmemusg, geoips_only=geoips_only)
            else:
                process(sectored, curr_sector, productlist, forcereprocess=forcereprocess,
                    sectorfile=sector_file, printmemusg=printmemusg, geoips_only=geoips_only)
            # MLS 20160126 Try this for memory usage ? Probably doesn't do anything
            gc.collect()
        else:
            log.info('{0} STARTING MULTIPROCESSING'.format(plog))
            try:
                orig_shape = [dsvars.shape for dss in data_file.datasets.values() for dsvars in
                              dss.variables.values()]
                sectored_shape = [dsvars.shape for dss in sectored.datasets.values() for dsvars in
                                  dss.variables.values()]
                log.info('Original data shape: {0}'.format(orig_shape))
                log.info('Sectored data shape: {0}'.format(sectored_shape))
            except:
                log.exception('Failed printing original and sectored data shapes.')
            # Need to pass all arguments, can not have = in args arg for Process
            sectors_run += [curr_sector.name]
            proc_args = (sectored, curr_sector, productlist, None, False, forcereprocess,
                         sector_file, printmemusg, geoips_only)
            mpp = multiprocessing.Process(target=process, args=proc_args)

            try:
                # Start multiprocessing
                mpp.start()
                # Don't append to jobs unless p.start() doesn't fail with OSError
                mp_jobs.append(mpp)
                DATETIMES['startmp_{0}{1}'.format(mpp.ident, mpp.name)] = datetime.utcnow()
                log.info('{0} MPLOG Starting process number: {1} sector: {2} {3}'.format(
                    plog, mp_num_procs, curr_sector.name, mp_num_procs))
                mp_num_procs += 1
                # print mpp
            except OSError:             # OSerror caused by a lack of memory
                log.info('{0} OSError (lack of memory) occurred when trying to start job. {1}'.format(
                    plog, curr_sector.name))
            # MLS 20160126 Try this for memory usage ? Probably doesn't do anything
            gc.collect()
            # Set the max_num_jobs just for log purposes.
            if len(mp_jobs) > mp_max_num_jobs:
                # This is purely for log purposes
                mp_max_num_jobs = len(mp_jobs)
        DATETIMES['end_{0}'.format(curr_sector.name)] = datetime.utcnow()
        sect_time = (DATETIMES['end_{0}'.format(curr_sector.name)] -
                     DATETIMES['start_{0}'.format(curr_sector.name)])
        log.info('{0} process {1} time: {2}'.format(plog, curr_sector.name, sect_time))
    else:
        if not mp_waiting:
            # If we hadn't been waiting, initialize the wait timer, for
            # log purposes. Probably is something in the multiprocessing
            # module that does this...
            mp_num_waits += 1
            DATETIMES['start_wait_time{0}'.format(mp_num_waits)] = datetime.utcnow()
            mp_waiting = True
        for job in mp_jobs:
            if not job.is_alive():
                log.info('MPLOG Removing job: {0} {1}'.format(job.ident, job.name))
                DATETIMES['endmp_{0}{1}'.format(job.ident, job.name)] = datetime.utcnow()
                mp_time = (DATETIMES['endmp_{0}{1}'.format(job.ident, job.name)] -
                           DATETIMES['startmp_{0}{1}'.format(job.ident, job.name)])
                log.info('{0} {1} ran for {2}'.format(job.ident, job.name, mp_time))
                mp_jobs.remove(job)
        if not mp_jobs:
            mp_num_times_cleared += 1
            log.info('MPLOG cleared out all multiprocessing processes')

    return mp_num_waits, mp_num_procs, mp_num_times_cleared, mp_max_num_jobs, mp_waiting, didmem

    # datetimes['endallproc_'+curr_sector.name] = datetime.utcnow()
    # datetimes['end_'+curr_sector.name] = datetime.utcnow()
    # log.info('sector '+curr_sector.name+' time: '+str(datetimes['end_'+curr_sector.name]-datetimes['start_'+curr_sector.name]))


def driver(data_file, sector_file, productlist=None, sectorlist=None, outdir=None, call_next=True,
           forcereprocess=False, queue=None, no_multiproc=False, mp_max_cpus=1, 
           printmemusg=False, separate_datasets=False, write_sectored_datafile=False, 
            write_registered_datafile=False):
    '''
    Produce imagery from a single input data file for any number of sectors and products.

    +--------------+-----------+---------------------------------------------------+
    | Parameters:  | Type:     | Description:                                      |
    +==============+===========+===================================================+
    | data_file:   | *SciFile* | An instantiated SciFile instance containing data. |
    +--------------+-----------+---------------------------------------------------+
    | sector_file: | *str*     | A SectorFile instance.                            |
    +--------------+-----------+---------------------------------------------------+

    +----------------+--------+-------------------------------------------------------------------+
    | Keywords:      | Type:  | Description:                                                      |
    +================+========+===================================================================+
    | sectorlist:    | *list* | A list containing names of sectors for which imagery              |
    |                |        | should be produced.                                               |
    |                |        | Will produce imagery for each requested sector.                   |
    |                |        |                                                                   |
    |                |        | **Default:** all sectors in sectorfilepath                        |
    |                |        | plus all available :doc:`dynamic sectors`                         |
    +----------------+--------+-------------------------------------------------------------------+
    | productlist:   | *list* | A list containing names of products for which                     |
    |                |        | imagery should be produced if possible.                           |
    |                |        |                                                                   |
    |                |        | **Default:** all products in: $GEOIPS/productfiles/`source_name`/ |
    +----------------+--------+-------------------------------------------------------------------+
    | outdir:        | *str*  | Output directory for final imagery.                               |
    |                |        |                                                                   |
    |                |        | **Default:** Derived from the sectorfile.                         |
    +----------------+--------+-------------------------------------------------------------------+
    | call_next:     | *bool* | **True:** run the next processing phase                           |
    |                |        |                                                                   |
    |                |        | **False:** exit at end                                            |
    |                |        |                                                                   |
    |                |        | **Default:** True                                                 |
    +----------------+--------+-------------------------------------------------------------------+
    | forcereprocess | *bool* | **True:** overwrite any previously created imagery                |
    |                |        |                                                                   |
    |                |        | **False:** do not overwrite previously created imagery            |
    |                |        |                                                                   |
    |                |        | **Default:** False                                                |
    +----------------+--------+-------------------------------------------------------------------+
    | no_multiproc   | *bool* | **True:** Use multiprocessing.                                    |
    |                |        |                                                                   |
    |                |        | **False:** Do not use multiprocessing.                            |
    |                |        |                                                                   |
    |                |        | **Default:** False                                                |
    +----------------+--------+-------------------------------------------------------------------+
    | queue          | *str*  | Name of a PBS queue to use when calling                           |
    |                |        | subsequent processing stages.                                     |
    |                |        |                                                                   |
    |                |        | **Default:** None                                                 |
    +----------------+--------+-------------------------------------------------------------------+
    | separate_datasets | *bool* | **True:** run on each dataset individually                     |
    |                   |        |                                                                |
    |                   |        | ** False:** run all datasets concurrently                      |
    |                   |        |                                                                |
    |                   |        | **Default:** False                                             |
    +----------------+--------+-------------------------------------------------------------------+
    | write_sectored_datafile| *bool* | **True:** write sectored datafile out to                  |
    |                        |        |                 $PRESECTORED_DATA_PATH                    |
    |                        |        |                                                           |
    |                        |        | ** False:** do not write out datafile                     |
    |                        |        |                                                           |
    |                        |        | **Default:** False                                        |
    +----------------+--------+-------------------------------------------------------------------+
    | write_registered_datafile| *bool* | **True:** write registered datafile out to                  |
    |                        |        |                 $PREREGISTERED_DATA_PATH                    |
    |                        |        |                                                           |
    |                        |        | ** False:** do not write out datafile                     |
    |                        |        |                                                           |
    |                        |        | **Default:** False                                        |
    +----------------+--------+-------------------------------------------------------------------+
    '''
    # If we are not calling this from driver.py, set these times
    if 'start' not in DATETIMES.keys():
        DATETIMES['start'] = datetime.utcnow()
    if 'afteropendatafile' not in DATETIMES.keys():
        DATETIMES['after_opendatafile'] = datetime.utcnow()

    try:
        mp_max_cpus = int(mp_max_cpus)
    except ValueError:
        raise ValueError('mp_max_cpus must be castable to an integer.')

    if int(mp_max_cpus) <= 0:
        raise ValueError('mp_max_cpus must be greater than or equal to 1.')
    elif int(mp_max_cpus) == 1:
        log.info('mp_max_cpus set to 1, not running multiprocessing')
        no_multiproc = True
    elif not MAXCPUS:
        log.info('env MAXCPUS not defined, not running multiprocessing')
        no_multiproc = True
    elif int(mp_max_cpus) > int(MAXCPUS):
        log.info('Maximum of {0} cpus, reducing from: {1}'.format(MAXCPUS, mp_max_cpus))
        mp_max_cpus = int(MAXCPUS)

    log.info('no_multiproc: {0}'.format(no_multiproc))

    geoips_only = False
    # Going to set this is process.py. Leave pass through of geoips_only in case
    # we want to pass command line arg in the future.
    #if not GEOIPS_OPERATIONAL_USER:
    #    geoips_only = True

    log.interactive('\n\n')
    log.interactive('Starting driver (git version)')
    print_mem_usage('start_of_driver {0} {1}'.format(data_file.source_name, data_file.datasets.keys()))
    log.info('Box: {0} Max CPUs: {1}'.format(socket.gethostname(), mp_max_cpus))
    # Need to set up __str__ and __repr__ for SciFile
    # log.interactive('Data Path: %s' % path)

    # If we are not running as an operational user, always reprocess existing products
    if not GEOIPS_OPERATIONAL_USER:
        forcereprocess = True

    if productlist:
        log.interactive('Requested products ""'.format(' '.join(productlist)))
    DATETIMES['startallsects'] = datetime.utcnow()

    mp_num_procs = 0
    mp_max_num_jobs = 0
    mp_jobs = []
    mp_waiting = False
    mp_num_waits = 0
    mp_num_times_cleared = 0
    waittimes = {}
    sectors_run = []
    log.info('sectors to run: {0}'.format(sector_file.sectornames()))
    orig_sectnames = sector_file.sectornames()
    sects = sector_file.getsectors()

    didmem = False
    # for curr_sector in sector_file.itersectors():
    # Please excuse the polling loop.. Haven't gotten around to
    #   fixing this.

    if sects:
        runfirst = []
        runsecond = []
        for sect in sects:
            if sect.name in ['CONUSGulfOfMexico','CONUSCentralPlains','CONUSSouthCentral','Caribbean_large','CONUSSouthEast']:
                runfirst += [sect]
            else:
                runsecond += [sect]
        sects = runsecond + runfirst

    while mp_jobs or sects:
        rs_ret = run_sectors(data_file, sector_file, productlist, sectorlist, forcereprocess, no_multiproc,
                             mp_max_cpus, printmemusg, sects, mp_jobs, mp_waiting, geoips_only,
                             sectors_run, mp_num_procs, mp_max_num_jobs, mp_num_waits, mp_num_times_cleared,
                             waittimes, didmem, separate_datasets, write_sectored_datafile,
                            write_registered_datafile)
        mp_num_waits, mp_num_procs, mp_num_times_cleared, mp_max_num_jobs, mp_waiting, didmem = rs_ret
    if not sects and not mp_jobs:
        log.info('MPLOG All jobs completed')

    log.interactive('DONE RUNNING {0} {1} {2}'.format(
        data_file.source_name, data_file.datasets.keys(), data_file))
    DATETIMES['end'] = datetime.utcnow()

    # Gather times for logging
    total_wait = timedelta(seconds=0)
    total_time = DATETIMES['end'] - DATETIMES['start']
    non_cspp_time = DATETIMES['end'] - DATETIMES['after_opendatafile']
    cspp_time = DATETIMES['after_opendatafile'] - DATETIMES['start']

    log.info('MPLOG Total number of jobs kicked off: {0}'.format(mp_num_procs))
    log.info('    MPLOG Maximum number of jobs running at once: {0}'.format(mp_max_num_jobs))
    log.info('    MPLOG Number of times queue was clear: {0}'.format(mp_num_times_cleared))
    log.info('    MPLOG Original list of sectors to run: {0}'.format(orig_sectnames))
    for num_wait in waittimes.keys():
        total_wait += waittimes[num_wait]
        log.info('    {0} waited for {1}'.format(num_wait, waittimes[num_wait]))
    log.info('Total wait time: {0} Num waits: {1} Total run time: {2} Max concurrent jobs {3} {4} {5}'.format(
        total_wait, mp_num_waits, total_time, mp_num_procs, mp_num_times_cleared,
        mp_max_num_jobs, socket.gethostname(), sectors_run))
    DATETIMES['endallsects'] = datetime.utcnow()
    total_proc_time = DATETIMES['endallsects'] - DATETIMES['startallsects']
    log.info('Total process time: {0}'.format(total_proc_time, socket.gethostname()))

    for currdttag in DATETIMES.keys():
        if 'endmp_' in currdttag:
            tag = currdttag.replace('endmp_', '')
            tag_time = DATETIMES['endmp_{0}'.format(tag)] - DATETIMES['startmp_{0}'.format(tag)]
            log.info('    process mp time {0}: {1} {2}'.format(tag, tag_time, socket.gethostname()))
    log.info('non-cspp time: {0}, {1}'.format(non_cspp_time, socket.gethostname()))
    log.info('CSPP Time: {0} {1}'.format(cspp_time, socket.gethostname()))
    log.info('Total Time: {0} {1} Numjobs: {2}'.format(total_time, socket.gethostname(), mp_num_procs))
    return 


def predict_sectors(platform_name, source_name, start_dt, end_dt):
    '''
    Attempt to find overlapping sectors using the overpass predictor.

    It appears that if no overpasses are found we will still continue to process with ALL sectors.
    I'm not sure why this would be needed.  Shouldn't we always be able to get a sector list here?
    '''
    opasses = pass_prediction([platform_name], [source_name], None, None, start_dt, end_dt,
                              force=True, single=True, quiet=True)
    if not opasses:
        return None
    # Since we found overpasses build the sector list
    sectorlist = []
    check_enddt = df.end_datetime
    if df.start_datetime == df.end_datetime:
        check_enddt = df.end_datetime + timedelta(hours=2)
    log.info('Matching overpasses between '+str(df.start_datetime)+' and '+str(check_enddt)+': ')
    for opass in opasses:
        if _FileNameBase.is_concurrent_with(opass.startdt, df.start_datetime, opass.enddt, check_enddt):
            log.info('\tOverlaps overpass {0}'.format(opass.opass))
            sectorlist.extend([yy.lower() for yy in opass.actualsectornames])
    return sectorlist


def _get_argument_parser():
    '''Create an argument parser with all of the correct arguments.'''
    parser = ArgParse()
    parser.add_arguments(['paths', 'separate_datasets', 'write_sectored_datafile', 'write_registered_datafile', 
                            'sectorlist', 'productlist', 'product_outpath', 'next', 'loglevel',
                          'forcereprocess', 'all', 'allstatic', 'alldynamic', 'tc', 'volcano', 'sectorfiles',
                          'templatefiles', 'no_multiproc', 'mp_max_cpus', 'queue', 'printmemusg'])
    return parser


if __name__ == '__main__':

    # Parse commandline arguments
    parser = _get_argument_parser()
    args = vars(parser.parse_args())
    args = parser.cleanup_args(args)

    # Set up logger
    root_logger, file_hndlr, email_hndlr = root_log_setup(loglevel=args['loglevel'], subject=EMAIL_SUBJECT)

    # Store the start time for generating statistics
    DATETIMES['start'] = datetime.utcnow()
    log.info('Starting main: {0}'.format(DATETIMES['start']))

    # Get the data path and check to be sure it exists
    runpaths = args['paths']
    for runpath in runpaths:
        if os.path.exists(runpath):
            log.interactive('Input path: {0}'.format(runpath))
        else:
            raise IOError('No such file or directory: {0}'.format(runpath))

    # Set up data file instance and read the metadata
    print_mem_usage('Before reading metadata')
    df = SciFile()
    df.import_metadata(runpaths)

    # If no sectors passed, run pass predictor to get list of sectors.
    # Allow search for dynamic sectors to start 9 hours before start time of data.
    dyn_start_dt = df.start_datetime - timedelta(hours=12)
    dyn_end_dt = df.end_datetime
    if df.start_datetime == df.end_datetime:
        dyn_end_dt = df.end_datetime + timedelta(hours=2)
    if not args['sectorlist']:
        args['sectorlist'] = []
        for ds in df.datasets.values():
            args['sectorlist'] = predict_sectors(ds.platform_name, ds.source_name, dyn_start_dt, dyn_end_dt)

    DATETIMES['after_opendatafile'] = datetime.utcnow()
    print_mem_usage('After reading metadata')

    # Create combined sectorfile for requested sectors
    sectfile = sectorfile.open(sectorlist=args['sectorlist'], productlist=args['productlist'],
                               sectorfiles=args['sectorfiles'], dynamic_templates=args['templatefiles'],
                               tc=args['tc'], volcano=args['volcano'], allstatic=args['allstatic'],
                               alldynamic=args['alldynamic'], start_datetime=dyn_start_dt,
                               end_datetime=df.end_datetime, actual_datetime=df.start_datetime,
                               scifile=df, quiet=True)

    log.info('\n\n')
    # Determine which sectors are needed and which aren't
    if args['sectorlist']:
        req_sects = sorted(args['sectorlist'])
        non_req_sects = sorted(list(set(sectfile.sectornames()) ^ set(req_sects)))
        log.info('\tRequested sectors: {0}'.format(req_sects))
        log.info('\n')
        log.info('\tUnused sectors: {0}'.format(non_req_sects))

    log.info('\n\n')

    log.info('\t\tSectors from files: ')
    try:
        for sectname in sorted(sectfile.sourcefiles.keys()):
            log.info('\t\t\t{0} {1}'.format(sectname, sectfile.sourcefiles[sectname]))
    except AttributeError:
        log.info('\t\t\t{0}'.format(sectfile))

    req_prods = []
    for ds in df.datasets.values():
        req_prods += sectfile.get_requested_products(ds.source_name, args['productlist'])
        pf = productfile.open2(ds.source_name, req_prods)
        if hasattr(pf, 'names'):
            log.info('\t\tProducts from files: ')
            for pfname in sorted(pf.names):
                log.info('\t\t\t{0}'.format(pfname))

    chans = []
    for ds in df.datasets.values():
        log.info('\n\n')
        # Get list of all possible channels required based on sectorfile and productlist
        chans += sectfile.get_required_vars(ds.source_name, args['productlist'])
        chans += sectfile.get_optional_vars(ds.source_name, args['productlist'])
    log.info('\tRequired channels: {0}'.format(sorted(chans)))
    log.info('\n')
    log.info('\tRequired sectors: {0}'.format(sorted(sectfile.sectornames())))
    log.info('\n')
    log.info('\tRequired products: {0}'.format(sorted(req_prods)))

    log.info('\n\n')

    # If chans or sectornames are empty, nothing needs the data we have. Print some additional info.
    if not chans or not sectfile.sectornames():
        if not chans:
            log.info('No data found for required sectors')
        log.info('You requested sectors:  {0}'.format(args['sectorlist']))
        log.info('You requested products: {0}'.format(args['productlist']))
        log.info('Actually defined:')
        sectfile.print_available(df.source_name)
        log.info('NO AVAILABLE SECTORS OR PRODUCTS FROM SECTORFILES')
    else:
        # JES: I would argue that this should all be moved inside the driver function.
        #      I also think that df should have an itersectors method and that all
        #      datafiles should be handled the same, regardless of how they are sectored.
        # MLS: How about
        #       df = SciFile(runpaths) above where the import_metadata was
        #           (no import_metadata, __init__ will automatically return metadata)
        #       Don't re-initialize SciFile object ever again, just subsequent import_datas.
        #       df.import_data(chans=chans,sector=curr_sector) in sector loop
        #           if it is a SECTOR_ON_READ type, it will only read for area_definition
        #           if it is not a SECTOR_ON_READ type, the first time through it will
        #               read everything, subsequently will just no-op because it already
        #               has all the data (we'll have to make sure the readers all
        #               handle this.)
        #       But then we have to make sure scifile cleans up after itself because
        #           we don't want all the data from all the sectors getting added
        #           to the object, and nothing ever disappearing.
        # If 'SECTOR_ON_READ' is specified in df.metadata, that means the reader
        # will be read one sector at a time within the sector loop, so just maintain
        # the empty dataset for now.
        if 'SECTOR_ON_READ' not in df.metadata['top'].keys():
            # Start a new one to get rid of METADATA dataset
            df = SciFile()
            df.import_data(runpaths, chans=chans)
        else:
            log.info(('Reader {0} performs sectoring at read time - ' +
                      'waiting to read until looping through sectors.').format(df.metadata['top']['readername']))
        # I was trying to avoid reopening sectorfile, but we need the real scifile
        # object attached to it, not the metadata scifile object. Maybe this would
        # be fixed if we did import_metadata then import_data on the same SciFile()
        # instance ... ?
        # Yes, it would.
        # Then we need to make it so scifile can handle returning an object with just 
        #   metadata and no datasets defined ! Or all our objects will have a dataset 
        #   named METADATA with {} in it. On the to do list.
        start_dt = df.start_datetime - timedelta(hours=9)
        sectfile = sectorfile.open(sectorlist=args['sectorlist'], productlist=args['productlist'],
                                   sectorfiles=args['sectorfiles'], dynamic_templates=args['templatefiles'],
                                   tc=args['tc'], volcano=args['volcano'], allstatic=args['allstatic'],
                                   alldynamic=args['alldynamic'], start_datetime=start_dt,
                                   end_datetime=df.end_datetime, actual_datetime=df.start_datetime,
                                   scifile=df, quiet=True)

        # MLS This is a good place to enter iPython in order to interrogate
        #       the UNSECTORED data file for development purposes.
        #   df.datasets.keys()
        #   df.datasets[<dsname>].variables.keys()
        #   df.datasets[<dsname>].variables[<varname>].min()
        #   df.datasets[<dsname>].variables[<varname>].max()
        # print 'UNSECTORED scifile object in driver: df.datasets'
        # print 'df.datasets[<dsname>].variables[<varname>]'
        # from IPython import embed as shell
        # shell()

        log.info('SciFile information:')
        try:
            log.info('\tstart_datetime: '+str(df.start_datetime))
            log.info('\tend_datetime: '+str(df.end_datetime))
        except:
            log.info('\tSomething undefined on SciFile object')

        if args['separate_datasets']:
            dfnew = SciFile()
            log.info('Running each dataset separately through driver')
            dfnew.metadata = df.metadata.copy()
            olddsname = None
            for dsname in df.datasets.keys():
                if olddsname:
                    dfnew.delete_dataset(olddsname)
                dfnew.add_dataset(df.datasets[dsname])
                if 'datasets' in dfnew.metadata and dsname in dfnew.metadata['datasets'].keys():
                    for key in dfnew._finfo.keys():
                        if key in dfnew.metadata['datasets'][dsname].keys():
                            dfnew.metadata['top'][key] = dfnew.metadata['datasets'][dsname]['platform_name']
                            dfnew.datasets[dsname].platform_name = dfnew.metadata['top']['platform_name']
                olddsname = dsname
                driver(dfnew, sectfile, productlist=args['productlist'], sectorlist=args['sectorlist'],
                   outdir=args['product_outpath'], call_next=args['next'],
                   forcereprocess=args['forcereprocess'], queue=args['queue'],
                   no_multiproc=args['no_multiproc'], mp_max_cpus=args['mp_max_cpus'],
                   printmemusg=args['printmemusg'], separate_datasets=args['separate_datasets'],
                   write_sectored_datafile=args['write_sectored_datafile'],
                   write_registered_datafile=args['write_registered_datafile'])

        else:
            driver(df, sectfile, productlist=args['productlist'], sectorlist=args['sectorlist'],
               outdir=args['product_outpath'], call_next=args['next'],
               forcereprocess=args['forcereprocess'], queue=args['queue'],
               no_multiproc=args['no_multiproc'], mp_max_cpus=args['mp_max_cpus'],
               printmemusg=args['printmemusg'], separate_datasets=args['separate_datasets'],
               write_sectored_datafile=args['write_sectored_datafile'],
                   write_registered_datafile=args['write_registered_datafile'])

