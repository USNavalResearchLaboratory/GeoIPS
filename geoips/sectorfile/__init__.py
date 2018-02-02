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

# Python Standard Libraries
import os
import logging
import glob
from datetime import datetime,timedelta


# Installed Libraries
from IPython import embed as shell
from lxml.etree import XMLSyntaxError


# GeoIPS Libraries
from .xml import XMLSectorFile, AllSectorFiles
from .dynamic import create_dynamic_xml_sectorfiles, choose_dynamic_xml_sectorfiles
import geoips.utils.plugin_paths as plugins

log = logging.getLogger(__name__)

sectorfile_classes = {'.xml': XMLSectorFile,
                     }

bigindent = '\n'+' '*60

__doc__ = '''
          The ``sectorfile`` package is used for reading, writing, and manipulating
          GeoIPS' :doc:`sectorfiles`.

          :docnote:`Some attention needs to be given to reworking this package's organization and documentation.  Maybe the XMLNode package should be moved into a larger XML package?`

          '''


def open(sectorfiles=[],
        dynamic_templates=[],
        sectorlist=None,
        productlist=None,
        tc=False,
        volcano=False,
        allstatic=False,
        alldynamic=False,
        allexistingdynamic=False,
        allnewdynamic=False,
        start_datetime=datetime.utcnow(),
        end_datetime=datetime.utcnow(),
        actual_datetime=None,
        one_per_sector=True,
        quiet=False,
        scifile=None,
        **kwargs
        ):
    '''
    Open :ref:`sectorfiles`.  Returns an instance of AllSectorFiles.

    :docnote:`Should figure out how to make datetime.utcnow() not evaluate prior to documentation.`

    +--------------------+------------+------------------------------------------------------------------+
    | Keyword:           | Type:      | Description:                                                     |
    +====================+============+==================================================================+
    | sectorfiles        | *list*     | A list of sectorfiles and/or directories.                        |
    |                    |            |                                                                  |
    |                    |            | Each sectorfile in the list will be opened and appended          |
    |                    |            | to the resulting AllSectorFiles instance. Directories            |
    |                    |            | are recursively searched for available sectorfiles               |
    |                    |            | each of which is opened and appended to the resulting            |
    |                    |            | AllSectorFiles instance.                                         |
    |                    |            |                                                                  |
    |                    |            | If either ``sectorfiles`` or ``dynamic_templates`` is not        |
    |                    |            | `None` only the sectorfiles and templates provided will          |
    |                    |            | be opened.                                                       |
    |                    |            |                                                                  |
    |                    |            | If both the ``sectorfiles`` and ``dynamic_templates``            |
    |                    |            | keywords are None, then all sectorfiles found in                 |
    |                    |            | plugins.paths['STATIC_SECTORFILEPATHS'] and all templates found in        |
    |                    |            | plugins.paths['TEMPLATEPATHS'] will be used.                              |
    |                    |            |                                                                  |
    |                    |            | **Default:** None                                                |
    +--------------------+------------+------------------------------------------------------------------+
    | dynamic_templates  | *list*     | A list of sectorfile templates and/or directories.               |
    |                    |            |                                                                  |
    |                    |            | Each template in the list will be opened and appended            |
    |                    |            | to the resulting AllSectorFiles instance. Directories            |
    |                    |            | are recursively searched for available sectorfiles               |
    |                    |            | each of which is opened and appended to the resulting            |
    |                    |            | AllSectorFiles instance.                                         |
    |                    |            |                                                                  |
    |                    |            | If either ``sectorfiles`` or ``dynamic_templates`` is not        |
    |                    |            | `None` only the sectorfiles and templates provided will          |
    |                    |            | be opened.                                                       |
    |                    |            |                                                                  |
    |                    |            | If both the ``sectorfiles`` and ``dynamic_templates``            |
    |                    |            | keywords are None, then all sectorfiles found in                 |
    |                    |            | plugins.paths['STATIC_SECTORFILEPATHS']` and all templates found in       |
    |                    |            | plugins.paths['TEMPLATEPATHS']` will be used.                             |
    |                    |            |                                                                  |
    |                    |            | .. note:: :docnote:`MINDY:` Ask Mindy to rework this one.        |
    |                    |            | It looks to me like this actually defaults to doing nothing      |
    |                    |            | since ``tc``, ``volcano``, and ``alldynamic`` all                |
    |                    |            | default to ``False``.                                            |
    |                    |            |                                                                  |
    |                    |            | **Default:** None                                                |
    +--------------------+------------+------------------------------------------------------------------+
    | sectorlist         | *list*     | A list of sector short-names to be opened in an                  |
    |                    |            | AllSectorFiles object.                                           |
    |                    |            |                                                                  |
    |                    |            | If None, then open all available sectors.                        |
    |                    |            |                                                                  |
    |                    |            | **Default:** None                                                |
    +--------------------+------------+------------------------------------------------------------------+
    | allstatic          | *bool*     | :docnote:`I'M NOT SURE WHAT THIS DOES`                           |
    |                    |            |                                                                  |
    |                    |            | **Default:** False                                               |
    +--------------------+------------+------------------------------------------------------------------+
    | alldynamic         | *bool*     | **True:** Shorthand for ``allexistingdynamic=True`` and          |
    |                    |            | ``allnewdynamic=True``                                           |
    |                    |            |                                                                  |
    |                    |            | **False:** :docnote:`I am not sure what this does!!!`            |
    |                    |            |                                                                  |
    |                    |            | **Default:** False                                               |
    +--------------------+------------+------------------------------------------------------------------+
    | allexistingdynamic | *bool*     | :docnote:`I'M NOT SURE WHAT THIS DOES`                           |
    |                    |            |                                                                  |
    |                    |            | **Default:** False                                               |
    +--------------------+------------+------------------------------------------------------------------+
    | allnewdynamic      | *bool*     | :docnote:`I'M NOT SURE WHAT THIS DOES`                           |
    |                    |            |                                                                  |
    |                    |            | **Default:** False                                               |
    +--------------------+------------+------------------------------------------------------------------+
    | tc                 | *bool*     | **True:** Run Tropical Cyclone dynamic sectors. This is          |
    |                    |            | shorthand for ``dynamic_templates=``\ :envvar:`TC_TEMPLATEFILE`. |
    |                    |            | This option will *always* add the Tropical Cyclone sectors       |
    |                    |            | to the list of sectors regardless of what else was passed.       |
    |                    |            |                                                                  |
    |                    |            | **False:** Do not run Tropical Cyclone dynamic sectors.          |
    |                    |            |                                                                  |
    |                    |            | :docnote:`IS THIS TRUE???`                                       |
    |                    |            |                                                                  |
    |                    |            | **Default:** False                                               |
    +--------------------+------------+------------------------------------------------------------------+
    | volcano            | *bool*     | **True:** Run Volcano dynamic sectors. This is shorthand         |
    |                    |            | for ``dynamic_templates=``\ :envvar:`VOLCANO_TEMPLATEFILE`.      |
    |                    |            | This option will *always* add the Volcano sectors                |
    |                    |            | to the list of sectors regardless of what else was passed.       |
    |                    |            |                                                                  |
    |                    |            | **False:** Do not run Volcano dynamic sectors.                   |
    |                    |            |                                                                  |
    |                    |            | :docnote:`IS THIS TRUE???`                                       |
    |                    |            |                                                                  |
    |                    |            | **Default:** False                                               |
    +--------------------+------------+------------------------------------------------------------------+
    | start_datetime     | *datetime* | :docnote:`I'M NOT SURE WHAT THIS DOES`                           |
    |                    |            |                                                                  |
    |                    |            | **Default:** datetime.utcnow()                                   |
    +--------------------+------------+------------------------------------------------------------------+
    | end_datetime       | *datetime* | :docnote:`I'M NOT SURE WHAT THIS DOES`                           |
    |                    |            |                                                                  |
    |                    |            | **Default:** datetime.utcnow()                                   |
    +--------------------+------------+------------------------------------------------------------------+
    | actual_datetime    | *datetime* | :docnote:`I'M NOT SURE WHAT THIS DOES`                           |
    |                    |            |                                                                  |
    |                    |            | **Default:** None                                                |
    +--------------------+------------+------------------------------------------------------------------+
    | one_per_sector     | *bool*     | :docnote:`I HAVE NO IDEA WHAT THIS DOES`                         |
    |                    |            |                                                                  |
    |                    |            | **Default:** True                                                |
    +--------------------+------------+------------------------------------------------------------------+
    | **kwargs           |            |                                                                  |
    +--------------------+------------+------------------------------------------------------------------+

    '''
    log.debug('sectorfile.open')
    if quiet:
        log.setLevel(35)
    sfs = []
    dts = []
    allsfs = set() 
    all_dynamic_sfs = []
    existing_dynamic_sfs = []
    expanded_dynamic_templates = []
    expanded_sectorfiles = []
    # THIS WAS SCREWING UP ON LOOPS when we just
    # added to dynamic_templates.  Need to create an
    # entirely new list so recursive call actually 
    # uses what was passed in, and not what dynamic_templates
    # ended up being the last time. Maybe this didn't
    # happen when dynamic_templates defaulted to None instead
    # of [] ?
    # Fails if dynamic_templates or sectorfiles is None
    if dynamic_templates:
        for dtemp in dynamic_templates:
            expanded_dynamic_templates += [dtemp]
    if sectorfiles:
        for sfile in sectorfiles:
            expanded_sectorfiles += [sfile]
        sectorfiles = [sf for sf in sectorfiles if os.path.splitext(sf)[-1] != '.dtd']
    else:
        sectorfiles = []


    #Only expand out all defaults if nothing is passed (otherwise, we just 
    #want to run what was passed)
    # Watch this - was previously passing/checking specifically False None (for dynamic_templates/sectorfiles)
    # Now pass [] for dynamic_templates and sectorfiles
    if not dynamic_templates and not allstatic and not allexistingdynamic and not \
        allnewdynamic and not tc and not volcano and not alldynamic:
        if len(sectorfiles) == 1 and os.path.isfile(sectorfiles[0]):
            log.debug('    Opening single sectorfile: '+sectorfiles[0])
            sectorfile = os.path.abspath(sectorfiles[0])
            sf_class = get_sectorfile_class(sectorfile)
            return sf_class(sectorfile,sectorlist,productlist,allstatic,allnewdynamic,allexistingdynamic,scifile=scifile)
        # If NOTHING passed in at all, default to allstatic and alldynamic (NEW! used to have 
        # to explicitly request dynamic - now looks for dynamic too.
        elif not sectorfiles:
            txt = ''
            if sectorlist != None:
                txt = 'that match sectorlist: '+' '.join(sectorlist)
            log.info('No sectorfile arguments passed, default to all static sectorfiles '+txt)
            allstatic=True
            alldynamic=True
            expanded_dynamic_templates = []

    if alldynamic == True:
        allexistingdynamic = allnewdynamic = True

    if tc is True:
        log.info("Argument 'tc' true")
        allexistingdynamic = True
        log.info("      using plugins.paths['TC_TEMPLATEFILES']="+str(plugins.paths['TC_TEMPLATEFILES']))
        for tctemplate in plugins.paths['TC_TEMPLATEFILES']:
            if os.path.exists(tctemplate):
                expanded_dynamic_templates.extend([tctemplate])
    if volcano is True:
        log.info("Argument 'volcano' true")
        allexistingdynamic = True
        # Either external volcano template, OR internal volcano template (one or the other...)
        log.info("      using plugins.paths['VOLCANO_TEMPLATEFILES']="+str(plugins.paths['VOLCANO_TEMPLATEFILES']))
        expanded_dynamic_templates.extend(plugins.paths['VOLCANO_TEMPLATEFILES'])
    if allstatic is True:
        log.info("Argument 'allstatic' true")
        log.info("      using plugins.paths['STATIC_SECTORFILEPATHS']="+str(plugins.paths['STATIC_SECTORFILEPATHS']))
        expanded_sectorfiles.extend(plugins.paths['STATIC_SECTORFILEPATHS'])
    if allexistingdynamic is True:
        log.info("Argument 'allexistingdynamic' true\n")
        log.info("      using plugins.paths['AUTOGEN_DYNAMIC_SECTORFILEPATH']="+str(plugins.paths['AUTOGEN_DYNAMIC_SECTORFILEPATH']))
        existing_dynamic_sfs.extend([plugins.paths['AUTOGEN_DYNAMIC_SECTORFILEPATH']])
    if allnewdynamic is True:
        log.info("Argument 'allnewdynamic' true\n")
        log.info("      using plugins.paths['TEMPLATEPATHS']="+str(plugins.paths['TEMPLATEPATHS']))
        expanded_dynamic_templates.extend(plugins.paths['TEMPLATEPATHS'])

        
    flatsfs = None
    if expanded_sectorfiles:
        log.debug('    expanded_sectorfiles: '+bigindent+bigindent.join(expanded_sectorfiles))
        sfs,flatsfs = uniq_list(expanded_sectorfiles,sectorlist=sectorlist,productlist=productlist,scifile=scifile)
        log.debug('    All static expanded_sectorfiles: '+bigindent+bigindent.join(sfs))
        allsfs = set(sfs)

    if expanded_dynamic_templates:
        log.debug('    expanded_dynamic_templates: '+bigindent+bigindent.join(expanded_dynamic_templates))
        dts,noflat = uniq_list(expanded_dynamic_templates,scifile=scifile)
        all_dynamic_sfs.extend(create_dynamic_xml_sectorfiles(dts,flatsfs,start_datetime,end_datetime,actual_datetime))
        log.debug('    All dynamic templates: '+bigindent+bigindent.join(dts))
    if existing_dynamic_sfs:
        log.debug('    Getting existing dynamic sectorfiles')
        edsfs,noflat = uniq_list(existing_dynamic_sfs,start_datetime,end_datetime,volcano=volcano,tc=tc,scifile=scifile)
        all_dynamic_sfs.extend(edsfs)
    if all_dynamic_sfs:
        allsfs.update(set(choose_dynamic_xml_sectorfiles(all_dynamic_sfs,
                                                 start_datetime,
                                                 end_datetime,
                                                 actual_datetime=actual_datetime,
                                                 sectorlist=sectorlist,
                                                 one_per_sector=one_per_sector)))
    allsfs = sorted(list(allsfs))

    return AllSectorFiles(allsfs,sectorlist,productlist,allstatic,allexistingdynamic,allnewdynamic,scifile=scifile)

def uniq_list(filelist,start_datetime=None,end_datetime=None,sectorlist=None,productlist=None,volcano=True,tc=True,scifile=None):
    outlist = []
    dyntype = ''
    if volcano and not tc:
        dyntype = 'volc'
    elif tc and not volcano:
        dyntype = 'tc'
    for file in filelist:
        if os.path.isdir(file):
            log.info('      Expanding path: '+file)
            if start_datetime != None:
                day_count = (end_datetime - start_datetime).days + 1
                log.debug(str(day_count)+' days, start_dt to end_dt: '+str(start_datetime)+' to '+str(end_datetime))
                datelist = []
                datelist.append(start_datetime.strftime('%Y%m%d'))
                datelist.append(end_datetime.strftime('%Y%m%d'))
                # MLS 20160218 This used to have () not [], how did that ever work? 
                # I guess () returns generator, so same in the end?
                for dt in [start_datetime+timedelta(n) for n in range(day_count)]:
                    datelist.append(dt.strftime('%Y%m%d'))
                datelist = set(datelist)
                new_list = []
                for datestr in datelist:
                    log.debug('  glob %s/%s*.xml'%(file,datestr))
                    log.debug('  glob %s/%04d/%04d/%s*.xml'%
                            (file,int(datestr[:4]),int(datestr[4:8]),datestr))
                    new_list.extend(glob.glob('%s/%s*%s*.xml'%
                            (file,datestr,dyntype)))
                    new_list.extend(glob.glob('%s/%04d/%04d/%s*%s*.xml'%
                            (file,int(datestr[:4]),int(datestr[4:8]),datestr,dyntype)))
                log.debug(new_list)
            else:
                new_list = glob.glob('%s/*%s*'%(file,dyntype))
            for new_file in new_list:
                if new_file not in outlist:
                    if sectorlist != None and open([new_file]).open_sectors(sectorlist) == None:
                        log.debug('            Requested Sectors not in file '+str(new_file)+' skipping: '+str(sectorlist))
                        continue
                    log.debug('        Appending file: '+new_file)
                    outlist.append(new_file)
                else:
                    log.debug('        '+new_file+' was already in list, not appending')
        else:
            if file not in outlist:
                if sectorlist == None or open([file]).open_sectors(sectorlist) != None:
                    log.debug('      Appending file: '+file)
                    outlist.append(file)
                else:
                    log.debug('            Requested Sectors not in file '+file+' skipping: '+str(sectorlist))
                    continue
            else:
                log.debug('      '+file+' was already in list, not appending')
    final_outlist = []
    nonsf_outlist = []
    for file in outlist:
        try:
            #print file
            if os.path.splitext(file)[-1] == '.dtd':
                continue
            sf_class = get_sectorfile_class(file)
            sf_class(file,sectorlist,productlist,scifile=scifile)
            final_outlist.append(file) 
        except KeyError:
            log.debug('     '+file+' not a Sectorfile Object, leaving out') 
            nonsf_outlist.append(file)
        except XMLSyntaxError:
            log.exception('Bad XML file!!! Delete or fix please. Not including in list. '+file)
       
    return final_outlist,nonsf_outlist

def get_sectorfile_class(sectorfile):
    basename, extension = os.path.splitext(sectorfile)
    return sectorfile_classes[extension]
