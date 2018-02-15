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
import socket
import logging
import getpass
from datetime import datetime

# Installed Libraries
try: from memory_profiler import profile
except: print 'Failed importing memory_profiler in process.py'
from matplotlib import rcParams
rcParams['path.simplify'] = False
if not os.getenv('GEOIPS_OPERATIONAL_USER'):
    from IPython import embed as shell
else:
    def shell():
        pass

# GeoIPS Libraries
import geoips.sectorfile as sectorfile
import geoips.productfile as productfile
from geoips.geoimg.geoimg import GeoImg
from geoips.scifile import SciFile
from geoips.utils.main_setup import ArgParse
from geoips.utils.log_setup import interactive_log_setup, root_log_setup
from geoips.utils.memusg import print_mem_usage

log = interactive_log_setup(logging.getLogger(__name__))
asterisks = '*'*60

__all__ = ['process']

__doc__ = '''
          ``process`` is called to produce all desired products from a single *pre-sectored** data file.
          Sectoring is performed by :doc:`driver <driver>`.  All input data should be unregistered to avoid
          problems with various products that require unregistered data.  ``process`` is typically only
          called from :doc:`driver <driver>`, however, it may be useful to call ``process`` using log output
          from :doc:`driver <driver>` for testing purposes.

          `product` performs multiple functions in the processing stream including:
          - registration of data to the input sector
          - calculation of any atmospheric corrections
          - application of any algorithms
          - production of temporary imagery (without borders, colorbars, titles, etc.)
          - stitching of multiple granules
          - stitching of multiple swaths
          - production of finalized imagery
          - imagery overlays **not yet implemented**

          '''

# MLS 20160203 No mem jumps now that I stopped storing subset! (Could be in
#           things it calls - but doesn't persist)
# Pulled the bulk of processing out of process so we can more easily run
#   memory_profiler on it. Please forgive the huge argument list...
#@profile
def create_imagery(data_file, sector, productlist, outdir,
                nofinal, forcereprocess, sectorfile,
                printmemusg,geoips_only,product,datetimes,plog):
    if productlist is None or product.lower() in productlist:
        datetimes['start_'+sector.name+product] = datetime.utcnow()
        pplog = plog+product
        log.info(pplog+' startprod')

        #print ''
        #print ''
        log.interactive('\n\n\n\n\n        STARTING PRODUCT: %s\n' % product)
        # Find the requested product
        try:
            curr_product = productfile.open_product(data_file.source_name, product, scifile=data_file)
        except AttributeError:
            log.info(pplog+' SKIPPING: Product %s not found for sector' % str(product))
            return None
        if not curr_product:
            log.info(pplog+' SKIPPING: Product %s not found for sector' % str(product))
            return None
        log.info(pplog+' FOUND: Product %s found.' % product)

        # Check whether required channels exist in data file, do this before 
        # day/night check.
        req_vars = curr_product.get_required_source_vars(data_file.source_name)

        # Skip if no required variables available for the current product
        if not data_file.has_all_vars(req_vars):
            log.warning(pplog+' SKIPPING: No required variables available')
            log.interactive('SKIPPING: No required variables available')
            return None

        if curr_product.day_ngt.lower() == 'day':
            if data_file.has_day(curr_product.day_ang) is False:
                log.info(pplog+' SKIPPING: Product %s requires daytime data, but none found.' % str(product))
                return None
        if curr_product.day_ngt.lower() in ['ngt', 'night']:
            if data_file.has_night(curr_product.ngt_ang) is False:
                log.info(pplog+' SKIPPING: Product %s requires nighttime data, but none found.' % str(product))
                return None


#            if forcereprocess is False and (os.path.exists(output_fname.name)):
#                log.warning('SKIPPING: Output file '+output_fname.name+' already exists. Not reprocessing! '+commands.getoutput('ls --full-time '+output_fname.name))
#                log.interactive('SKIPPING: Output file '+output_fname.name+' already exists. Not reprocessing! '+commands.getoutput('ls --full-time '+output_fname.name))
#                continue
#

        # This is where we actually run the processing method on the data
        log.info(pplog+'    Opening GeoImg...')
        tag = sector.name+product
        datetimes['startalg_'+tag] = datetime.utcnow()
        #img = GeoImg(subset, sector, sectorfile=sectorfile, product=curr_product)
        intermediate_data_output=False
        if hasattr(sector.area_info,'intermediate_data_output'):
            intermediate_data_output=sector.area_info.intermediate_data_output
        img = GeoImg(data_file, sector, intermediate_data_output=intermediate_data_output,sectorfile=sectorfile, product=curr_product)

        print_mem_usage(tag+' after opening GeoImg',printmemusg)


        # This should not be necessary - we should filter these out before actually processing.
        # But probably not a bad idea to have a catch in at this point too anyway.
        # Note img.coverage forces registering and processing data. Was not working when I
        #   passed intermediate_data_output to produce_imagery, but now that I set it in
        #   GeoImg instantiation, should be fine. Might want to address the fact that we don't
        #   want to fully register / process to check coverage, but for now we'll leave it the
        #   way it is.
        # Okay, seriously, we have to quit using blank except statements everywhere.  We've got
        #   to fix the code so this isn't needed.  It makes debugging completely impossible!
        #   Please please please stop it!
        try:
            currcovg = img.coverage()
        except Exception as err:
            log.exception('Failed creating image for '+curr_product.name+', SKIPPING')
            log.exception(err.message)
            return None
        if currcovg > 0.0:
            log.info('\n\n\n\n        Running GeoImg.produce_imagery for TEMPORARY SINGLE GRANULE image... \n')
            img.produce_imagery(geoips_only=geoips_only,datetimes=datetimes,datetimes_name=tag)
        else:
            log.info('\n\n\n\n'+pplog+'        TEMPORARY SINGLE GRANULE image had 0.0% coverage, '+str(currcovg)+'% !!! SKIPPING '+sector.name+' '+product+' ALTOGETHER!!... \n')
            return None

        # Comment out above and uncomment belo For testing purposes -
        # Comment out everything after this too to write all temp files directly to GeoIPS final
        #img.produce_imagery(final=True, clean_old_files=False,geoips_only=geoips_only)
        print_mem_usage(tag+' after writing granule image',printmemusg)
        datetimes['endalg_'+tag] = datetime.utcnow()

        datetimes['startmergegran_'+tag] = datetime.utcnow()

        # Set 'NO_GRANULE_COMPOSITES' in the metadata if granules should not be composited
        # (ie, geostationary, model data, etc)
        if 'NO_GRANULE_COMPOSITES' in data_file.metadata.keys() \
            and data_file.metadata['NO_GRANULE_COMPOSITES']:
            log.info('    NO_GRANULE_COMPOSITES set in SciFile Metadata - no granule or swath compositing')
            finalimg = img
            finalimg.merged_type = 'FULLCOMPOSITE'
            # This is necessary for overlays - expects imagery in fullcomposites directory.
            # Need a better method for this. Maybe always run merge_granules, and put special case in geoimg ?
            img.produce_imagery(geoips_only=geoips_only,datetimes=datetimes,datetimes_name=tag)
        else:
            log.info('\n\n\n\n       '+pplog+' Running merge_granules for TEMPORARY SWATH image... \n')
            swathimg = img.merge_granules()

            # Sometimes when trying to merge swaths, another process will delete our current merged img
            # before we can use it. Wrap all merges / produce_imagerys in try except for any file that could
            # potentially be deleted before we use it.
            try:
                log.info('\n\n\n\n       '+pplog+' Running produce_imagery for TEMPORARY SWATH image... \n')
                swathimg.produce_imagery(geoips_only=geoips_only)
            except (IOError,OSError),resp:
                log.error(str(resp)+pplog+' Failed writing TEMPORARY SWATH image. Someone else did it for us? Skipping to next product')
                return None
            # sector.composite_on specifies whether we want to do swath composites
            # for this particular sector. Some sectors in arctic / antarctic do
            # not need composited, because all swaths overlap.
            if sector.composite_on:
                log.info('\n\n\n\n       '+pplog+' Running merge_swaths and produce_imagery for TEMPORARY FULLCOMPOSITE image... \n')
                try:
                    finalimg = swathimg.merge_swaths()
                except (IOError,OSError),resp:
                    log.error(str(resp)+pplog+' Failed merging swaths. Someone else did it for us? Skipping to next product')
                    return None
                try:
                    finalimg.produce_imagery(geoips_only=geoips_only)
                except (IOError,OSError),resp:
                    log.error(str(resp)+pplog+' Failed writing TEMPORARY FULLCOMPOSITE image. Someone else did it for us? Skipping to next product')
                    return None
            # If we are not merging swaths, just set finalimg to the swathimg
            else:
                log.info('\n\n\n\n       '+pplog+' Compositing turned off for current sector '+sector.name+', not running temporary fullcomposite image... \n')
                finalimg = swathimg
                # This is necessary for overlays - expects imagery in fullcomposites directory.
                # Need a better method for this. Maybe always run merge_granules, and put special case in geoimg ?
                finalimg.merged_type = 'FULLCOMPOSITE'
                finalimg.produce_imagery(geoips_only=geoips_only,datetimes=datetimes,datetimes_name=tag)

        datetimes['endmergegran_'+tag] = datetime.utcnow()
        log.info(pplog+'Done merging granules')
        print_mem_usage(tag+' after merge',printmemusg)
        # If the finalimg is > 40% coverage, create the final images with
        # coast lines, legends, gridlines.
        curr_covg = sector.min_total_cover
        # If min_cover defined in product file, use that, not sector coverage.
        if curr_product.min_cover != None:
            curr_covg = curr_product.min_cover
        if finalimg.coverage() > curr_covg:
            log.info('\n\n\n\n   '+pplog+' Running GeoImg.produce_imagery for FINAL MERGED images... Coverage greater than specified coverage of: '+str(curr_covg)+' \n')
            # These get written to GeoIPS final, nexsat, TC, etc, as needed.
            try:
                # Note produce_imagery method actually sets self._is_final using the passed
                # 'final' argument, which is relied upon
                # in determining filenames / output data type (data files or imagery files)
                curr_geoips_only = check_if_testonly(finalimg, geoips_only)
                finalimg.produce_imagery(final=True, geoips_only=curr_geoips_only)
            except (IOError,OSError),resp:
                log.error(str(resp)+pplog+' Failed writing FINAL MERGED image. Someone else did it for us? Skipping to next product')
                return None
            print_mem_usage(tag+' after final merge',printmemusg)
        # Check the special multi-source product type,
        # create anything that this data file kicks off
        # (anything marked as 'runonreceipt' in productfile)
        # This is NOT tied to finalimg.produce_imagery because there are
        #   many different data types that can go into a single
        #   multisource product.  We do not want to limit
        #   multisource product generation on the coverage of the CURRENT
        #   data.  There might be other layers that have sufficient
        #   coverage - always check. STITCHED, for example!
        finalimg.create_multisource_products()
        # When we turn on multisource products, make sure they are getting written in create_multisource_products
        # This is writing out a final image regardless of percent coverage, not what we want!
        #try:
        #    # Didn't I write this out in create_multisource_products ?
        #    finalimg.produce_imagery(final=True, geoips_only=geoips_only)
        #except (IOError,OSError),resp:
        #    log.error(str(resp)+pplog+' Failed writing FINAL MERGED image. Someone else did it for us? Skipping to next product')
        #    return None

        log.info(pplog+' endprod')
        datetimes['end_'+tag] = datetime.utcnow()


def check_if_testonly(finalimg, geoips_only):
    testonly = geoips_only
    if not os.getenv('GEOIPS_OPERATIONAL_USER'):
        log.info('  Test only set: GEOIPS_OPERATIONAL_USER not defined')
        testonly = True
    # Currently you can set "test" in destinations list, OR set
    # testonly attribute on sector tag to turn off external dests
    # from sectorfiles.  Set on product tag to turn off external
    # dests from productfiles.
    sect = finalimg.sector
    prod = finalimg.product
    srcs = finalimg.sector.sources
    df = finalimg.datafile
    if sect.test_on or sect.testonly or\
       prod.testonly:
        log.info('  Test only set: finalimg.sector.test_on: ' +
                 str(sect.test_on) +
                 ', finalimg.sector.testonly: ' + str(sect.testonly) +
                 ', finalimg.product: ' + str(prod.testonly))
        testonly = True

    # Also can set testonly flag on entire source, or individual product
    # in sectorfile.
    if srcs and \
       (srcs.testonly(df.source_name) or srcs.testonly(df.source_name,
                                                       prod.name)):
        log.info('  Test only set: sources({0},{1}): {2}, sources({3}): {4}'.
                 format(df.source_name, prod.name,
                        srcs.testonly(df.source_name, prod.name),
                        df.source_name, srcs.testonly(df.source_name)))
        testonly = True

    return testonly

# MLS 20160203 monitor - mem jump at for product in sector.products(.5G)
#@profile
def process(data_file, sector, productlist=None, outdir=None, nofinal=False, forcereprocess=False, sectorfile=None,printmemusg=False,geoips_only=False):
    '''
    Produce imagery from a single pre-sectored data file.  Will stitch granules
    and (if requested) swaths into composite final imagery.


    +-------------+-----------+---------------------------------------------------------------------------+
    | Parameters: | Type:     | Description:                                                              |
    +=============+===========+===========================================================================+
    | data_file:  | *SciFile* | An instance of SciFile containg the data to be processed.                 |
    +-------------+-----------+---------------------------------------------------------------------------+
    | sector:     | *Sector*  | An instance of sectorfile.Sector for which products should be created.    |
    +-------------+-----------+---------------------------------------------------------------------------+

    +-----------------+--------+--------------------------------------------------------+
    | Keywords:       | Type:  | Description:                                           |
    +=================+========+========================================================+
    | productlist:    | *list* | A list of strings naming the products to be produced   |
    +-------------+-----------+---------------------------------------------------------+
    | outdir:         | *str*  | Output directory for final imagery.                    |
    |                 |        |                                                        |
    |                 |        | **Default:** Derived from the sectorfile.              |
    +-----------------+--------+--------------------------------------------------------+
    | nofinal:        | *bool* | **True:** produce finalized imagery with coastlines,   |
    |                 |        | gridlines, colorbar, title, etc.                       |
    |                 |        |                                                        |
    |                 |        | **False:** only produce temporary imagery.             |
    |                 |        |                                                        |
    |                 |        | **Default:** False                                     |
    +-----------------+--------+--------------------------------------------------------+
    | forcereprocess: | *bool* | **True:** overwrite any previously created imagery     |
    |                 |        |                                                        |
    |                 |        | **False:** do not overwrite previously created imagery |
    |                 |        |                                                        |
    |                 |        | **Default:** False                                     |
    +-----------------+--------+--------------------------------------------------------+

    '''
    plog = 'ppy'+sector.name

    datetimes = {}
    datetimes['start_sect'+sector.name] = datetime.utcnow()
    log.info(plog+' start')

    #Print out box name
    log.interactive('    ENTERING GEOIPS PROCESSING')
    log.info('\nBox: %s\nSource: %s\nSatellite: %s\nData Provider: %s\n' %
            (socket.gethostname(), data_file.source_name,data_file.platform_name,data_file.dataprovider))

    #Print info
    log.info(plog+' Current Sector: %s\n\n' % sector.name)
    #log.debug('Current Product:\n%s\n\n' % product)

    #This is not going to work for now.  Need to work on this.
    #try:
    #    if product.product_args.best_possible_pixel_height > sector.master_info.pixel_height:
    #        sector.master_info.pixel_height = product.product_args.best_possible_pixel_height
    #        sector.master_info.num_lines = product.product_args.best_possible_pixel_height / sector.master_info.num_lines
    #    if product.product_args.best_possible_pixel_width > sector.master_info.pixel_width:
    #        sector.master_info.pixel_width = product.product_args.best_possible_pixel_width
    #        sector.master_info.num_samples = product.product_args.best_possible_pixel_height / sector.master_info.num_samples
    #except AttributeError:
    #    log.info('best_possible_pixel_width/height not defined for product, using sector pixel_width/height')

    #shell()
    #if sector.atcf_on:
        ##CALL ARCHER data_file.name sector.source_info.node.sourceflattextfile
    for product in sector.get_requested_products(data_file.source_name,productlist):
        create_imagery(data_file, sector, productlist, outdir,
                nofinal, forcereprocess, sectorfile,
                printmemusg,geoips_only,product,datetimes,plog)
    datetimes['end_sect'+sector.name] = datetime.utcnow()
    log.info(plog+' endsect')
    for sttag in sorted(datetimes.keys()):
        if 'start_' in sttag:
            tag = sttag.replace('start_','')
            try:
                log.info('process time %-40s: '%tag+str(datetimes['end_'+tag]-datetimes['start_'+tag])+' '+socket.gethostname())
            except:
                log.info('WARNING! No end time for '+sttag)
        if 'startalg_' in sttag:
            tag = sttag.replace('startalg_','')
            try:
                log.info('process algorithm time %-40s: '%tag+str(datetimes['endalg_'+tag]-datetimes['startalg_'+tag])+' '+socket.gethostname())
            except:
                log.info('WARNING! No end time for '+sttag)
        if 'startmergegran_' in sttag:
            tag = sttag.replace('startmergegran_','')
            try:
                log.info('process merge granules time %-40s: '%tag+str(datetimes['endmergegran_'+tag]-datetimes['startmergegran_'+tag])+' '+socket.gethostname())
            except:
                log.info('WARNING! No end time for '+sttag)
        if 'startplot_' in sttag:
            tag = sttag.replace('startplot_','')
            try:
                log.info('process plot time %-40s: '%tag+str(datetimes['endplot_'+tag]-datetimes['startplot_'+tag])+' '+socket.gethostname())
            except:
                log.info('WARNING! No end time for '+sttag)


def _get_argument_parser():
    '''Create an argument parser with all of the correct arguments.'''
    parser = ArgParse()
    parser.add_arguments(['file',
                          'sector',
                          'productlist',
                          'sectorfiles',
                          'forcereprocess',
                          'product_outpath',
                          'nofinal',
                          'loglevel',
                        ])
    return parser

if __name__ == '__main__':
    #Set all of these to None for uncaught exeption handling
    emailsubject = 'GIProcess'
    email_hndlr = None
    root_logger = None
    combined_sf = None
    args = {'file':None, 'sectorfiles':[]}

    #Parse commandline arguments
    parser = _get_argument_parser()
    args = vars(parser.parse_args())
    args = parser.cleanup_args(args)

    #[callingscript,satellite,sensor,datasource,date,sector,product,rest] = os.path.basename(args['file']).split('_',7)
    root_logger, file_hndlr, email_hndlr = root_log_setup(loglevel=args['loglevel'], subject=emailsubject)


    #Open the datafile
    df = SciFile()
    df.import_data([args['file']])

    #This sectorfiles argument should be reduced to a single string rather than a list...
    sectfile = sectorfile.open(args['sectorfiles'],scifile=df)
    sector = sectfile.open_sector(args['sector'],scifile=df)

    #Get the product
    pf = productfile.open_product(df.source_name, args['product'], scifile=df)

    geoips_only=False
    # Set this in check_if_testonly. May want to pass argument at some point,
    # so leave pass through of geoips_only.
    #if not os.getenv('GEOIPS_OPERATIONAL_USER'):
    #    geoips_only=True

    #Call process
    process(df,
            sector,
            productlist = args['productlist'],
            outdir = args['product_outpath'],
            nofinal = args['nofinal'],
            forcereprocess = args['forcereprocess'],
            sectorfile=sectfile,
            geoips_only=geoips_only
           )

