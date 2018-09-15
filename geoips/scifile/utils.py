import os
from datetime import datetime, timedelta
from glob import glob
import h5py
import numpy as np
import logging
from geoips.utils.plugin_paths import paths as gpaths

log = logging.getLogger(__name__)

def get_filename(basedir, source_name, secclass, sector, sdt, edt, platform_name, numfiles, dataprovider=None, filetype='h5'):
    if isinstance(numfiles, int):
        numfilesstr = '%03d'%(numfiles)
    else:
        numfilesstr = '%s'%(numfiles)
    if isinstance(sdt, datetime):
        sdtstr = sdt.strftime('%Y%m%d.%H%M%S')
    else:
        sdtstr = sdt
    if isinstance(edt, datetime):
        edtstr = edt.strftime('%Y%m%d.%H%M%S')
    else:
        edtstr = edt

    suf = '.'+filetype

    uniq_hash = sector.uniq_hash

    dirname = '%s/%s_%s'%(basedir,source_name,secclass)
    baseoutfilename = '%s_%s-%s_%s_%s_%s_%s_%s'%(
                        sector.name,    
                        sdtstr,
                        edtstr,
                        platform_name,
                        source_name,
                        dataprovider,
                        numfilesstr,
                        uniq_hash,
                    )
    return dirname, baseoutfilename, suf

def minrange(start_date, end_date):
    '''Check one min at a time'''
    log.info('in minrange')
    tr = end_date - start_date
    for n in range(tr.seconds / 60):
        yield start_date + timedelta(seconds = (n*60))

def daterange(start_date, end_date):
    '''Check one day at a time. 
        If end_date - start_date is between 1 and 2, days will be 1,
        and range(1) is 0. So add 2 to days to set range'''
    log.info('in minrange')
    tr = end_date - start_date
    for n in range(tr.days + 2):
        yield start_date + timedelta(n)

def hourrange(start_date, end_date):
    '''Check one hour at a time. '''
    log.info('in hourrange')
    tr = end_date - start_date
    for n in range(tr.days*24 + tr.seconds / 3600 ):
        yield start_date + timedelta(seconds = (n*3600))

def find_datafiles_in_range(sector, platform_name, source_name, min_time, max_time, basedir=gpaths['PRESECTORED_DATA_PATH'], dataprovider=None, filetype='h5'):
    secclass = '*'
    numfiles = '*'
    edtstr = '*'
    filenames = []
    if (min_time - max_time) < timedelta(minutes=30):
        for sdt in minrange(min_time, max_time):
            sdtstr = sdt.strftime('%Y%m%d.%H%M*')
            dirname, baseoutfilename, suf =  get_filename(basedir, source_name, secclass, sector, sdtstr, edtstr, platform_name, numfiles, dataprovider, filetype)
            filenames += glob(os.path.join(dirname,baseoutfilename+suf))
    return filenames

def write_datafile(basedir, datafile, sector, secclass=None, filetype='h5'):
    if filetype != 'h5':
        raise TypeError('Currently only h5 filetypes supported for write')


    if not secclass and datafile.security_classification:
        secclass = datafile.security_classification.replace('/','-')
        for ds in datafile.datasets.values():
            if 'SECRET' in ds.security_classification or '\/\/' in ds.security_classification:
                secclass = ds.security_classification.replace('/','-')
    elif secclass:
        secclass = secclass.replace('/','-')

    sdt = datetime.strptime('99991231','%Y%m%d')
    edt = datetime.strptime('19000101','%Y%m%d')
    #pnames = []
    #snames = []
    numfiles = len(datafile.datafiles.keys())
    for ds in datafile.datasets.values():
        #pnames += [ds.platform_name]
        #snames += [ds.source_name]
        if ds.start_datetime < sdt:
            sdt = ds.start_datetime
        if ds.end_datetime > edt:
            edt = ds.end_datetime

    #pnames = list(set(pnames))
    #snames = list(set(snames))

    dirname, baseoutfilename, suf = get_filename(basedir, 
                datafile.source_name, 
                secclass, 
                sector, 
                sdt, edt, 
                datafile.platform_name,
                numfiles,
                datafile.dataprovider,
                )

    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    outfilename = os.path.join(dirname,baseoutfilename+suf)
    ii = 0
    while os.path.exists(outfilename):
        newbaseoutfilename = '%s-%03d%s'%(baseoutfilename,ii,suf)
        outfilename = os.path.join(dirname, newbaseoutfilename)
        ii+=1
    log.info('Writing out %s SciFile data file: %s'%(suf,outfilename))
    datafile.write(outfilename, filetype=filetype)


def recurse_update_dictionary(old_base_dict, new_base_dict, key):
    if key not in new_base_dict.keys():
        new_base_dict[key] = old_base_dict[key]
    else:
        if isinstance(old_base_dict[key], dict):
            for new_key in old_base_dict[key].keys():
                recurse_update_dictionary(old_base_dict[key], new_base_dict[key], new_key)
    del old_base_dict[key]

def update_dictionary(base_dict, new_key, old_key):
    if new_key not in base_dict.keys():
        base_dict[new_key] = base_dict[old_key]
    else:
        if isinstance(base_dict[old_key], dict):
            for key in base_dict[old_key].keys():
                recurse_update_dictionary(base_dict[old_key], base_dict[new_key], key)
    del base_dict[old_key]

def rename_dataset(base_dsname, metadata, gvars, datavars):
    ''' Create a unique dataset name based on platform_name, 
        source_name, and start_datetime. This allows for 
        simpler reader definitions, and scifile can handle
        ensuring the separate datasets are unique'''

    # Find new, unique dataset name
    dsname = base_dsname
    if metadata['top']['platform_name'] not in base_dsname:
        dsname += '_'+metadata['top']['platform_name']
    if metadata['top']['source_name'] not in base_dsname:
        dsname += '_'+metadata['top']['source_name']

    dtstr = datetime.strftime(metadata['top']['start_datetime'], '%Y%m%d.%H%M%S')
    if dtstr not in base_dsname:
        dsname += '_'+dtstr

    # Get rid of the old dataset names, and create the new ones
    update_dictionary(metadata['datavars'], dsname, base_dsname)
    update_dictionary(metadata['gvars'], dsname, base_dsname)
    update_dictionary(metadata['ds'], dsname, base_dsname)
    update_dictionary(datavars, dsname, base_dsname)
    update_dictionary(gvars, dsname, base_dsname)

    from .containers import _empty_finfo as empty_info
    for key in empty_info.keys():
        if not metadata['ds'][dsname][key]:
            metadata['ds'][dsname][key] = metadata['top'][key]


def get_props_from_metadata(metadata, vartype, dsname, varname):
    '''
        metadata fields always specified:
            metadata['top']
            metadata['datasets'][dsname]
            metadata['variables'][dsname][varname]
            metadata['geolocation_variables'][dsname][varname]

        pull finfo from top
        pull dsinfo from 'datasets'
            default to 'top' if a particular field is not specified
        pull varinfo from 'variables' or 'geolocation_variables'
            default to 'datasets' if a particular field is not specified in
                '(geolocation_)variables'
            derfault to 'top' if a particular field is not specified in
                '(geolocation_)variables' or 'datasets'
    '''

    # If varname is passed, we need to fill in varinfo keys
    if varname:
        from .containers import _empty_varinfo as empty_info
    # else if dsname is passed, we need to fill in dsinfo keys
    elif dsname:
        from .containers import _empty_dsinfo as empty_info
    # else we're filling in finfo keys
    else: 
        from .containers import _empty_finfo as empty_info

    varinfo = {}

    # Default to top level metadata values
    for key,val in metadata['top'].items():
        if key in empty_info.keys():
            varinfo[key] = val

    # Keep going if a dataset name was specified:
    if dsname and dsname in metadata[vartype].keys():
        # If we have dsinfo defined at dataset level, use those values
        if dsname in metadata['ds'].keys():
            for key,val in metadata['ds'][dsname].items():
                if key in empty_info.keys() and val is not None:
                    varinfo[key] = val
        # Now, if the field is set at the variables or geolocation_variables
        # level, use the value from that level
        if varname and varname in metadata[vartype][dsname].keys():
            for key,val in metadata[vartype][dsname][varname].items():
                if key in empty_info.keys() and val is not None:
                    varinfo[key] = val
    #from IPython import embed as shell
    #shell()

    return varinfo

def recursively_load_dict_contents_from_group(h5file, path):
    ans = {}
    for key, item in h5file[path].items():
        # Put %fs% back to / in keys
        pathkey = key
        key = key.replace('%fs%','/')
        # Need to apply the same reverse operations that were applied in save_dict
        if isinstance(item, h5py._hl.dataset.Dataset):
            if isinstance(item.value, (str, unicode)):
                # Put %fs% back to / in values
                ans[key] = item.value.replace('%fs%','/')
                # Turn string True/False back into bool
                if ans[key] == 'True':
                    ans[key] = True
                if ans[key] == 'False':
                    ans[key] = False
                if ans[key] == 'None':
                    ans[key] = None

                '''NOTE if key == 'sector_definition', we need to do
                    ans[key] = sectorfile.open_sector(ans[key]) 
                    to fully restore the saved metadata dictionary
                    That will require more testing that I'm going to do right now.
                '''

                # Turn string datetime back into datetime obj
                try:
                    ans[key] = datetime.strptime(ans[key], '%Y%m%d%H%M%S.%f')
                except:
                    pass
            # These should work as straight hdf5 variable types
            elif isinstance(item.value, (np.ndarray, np.int64, np.float64, bytes)):
                ans[key] = item.value 
            elif isinstance(item.value, (np.float32, np.int32, int, np.uint64)):
                ans[key] = item.value
            # Added these for AHI / ABI metadata
            elif isinstance(item.value, (np.uint8, np.uint16, np.uint32)):
                ans[key] = item.value
        # If we are a group, recursively read in the rest of the levels
        elif isinstance(item, h5py._hl.group.Group):
            islist = True
            anslist = []
            # First check if it is a specially designated "list" dictionary 
            # Keys of dictionary all specified as listXXX, which should be 
            # expanded out to a list of the dictionary values
            # Make sure to sort the keys so the list is reconstructed in the
            # same order.
            for ffkey in sorted(h5file[path+pathkey].keys()):
                if 'list' in ffkey:
                    anslist += [h5file[path+pathkey][ffkey].value]
                elif 'list' not in ffkey:
                    islist = False
                if islist:
                    ans[key] = anslist
            # If it is not a list, then it is a regular old dictionary, and 
            # we need to recursively read in the rest of the levels.
            if not islist:
                ans[key] = recursively_load_dict_contents_from_group(h5file, path+pathkey+'/')
    return ans

def recursively_save_dict_contents_to_group(df, path, dic):
    for key, item in dic.items():
        # Always replace / in keys, otherwise it will break it up
        # when storing within hdf5 path (since each level is 
        # separated by / in group, so it makes a VERY deep
        # dict when trying to store a file path). Reverse
        # this process when reading.
        val = path+key.replace('/','%fs%')

        if isinstance(item, (str, unicode)):
            df[val] = item
        
        # THIS HAS TO GO BEFORE int instance, or it will 
        # match int, and fail to actually be written to 
        # hdf5 because bool is unsupported
        elif isinstance(item, bool):
            df[val] = str(item)

        # This was the original set of numpy types
        elif isinstance(item, (np.ndarray, np.int64, np.float64, bytes)):
            df[val] = item
       
        # I added these and they seem to work.
        elif isinstance(item, (np.float32, np.int32, int, np.uint64)):
            df[val] = item

        # Added these for AHI / ABI metadata
        elif isinstance(item, (np.uint8, np.uint16, np.uint32)):
            df[val] = item

        # If the current item is a dictionary, recursively start
        # writing the dictionary to the hdf5 group
        elif isinstance(item, dict):
            recursively_save_dict_contents_to_group(df, val+'/', item)

        # Can't natively store a list, so convert it to a dictionary 
        # with keys listXXXXX, if all keys in a dictionary on read are
        # named listXXXXX, then convert it back to a list on read.
        elif isinstance(item, list):
            tempdic = {}
            jj = 0
            for ii in item:
                tempdic['list%05d'%jj] = ii
                jj += 1
            recursively_save_dict_contents_to_group(df, val+'/', tempdic)

        # Need to store datetime as string, switch it back on read.
        elif isinstance(item, datetime):
            df[val] = item.strftime('%Y%m%d%H%M%S.%f')
        
        # If all else fails, see if it is None. isinstance(item, NoneType)
        # didn't work, so just test it directly.
        elif item == None:
            df[val] = 'None'

        else:
            from geoips.sectorfile.xml import Sector
            '''NOTE This needs to be added to recursively_load_dict_contents_from_group
                in order to restore the 'sector_definition' metadata dictionary entry
                on read.  That will require more testing that I'm going to do right now.
            '''
            if isinstance(item, Sector):
                df[val] = item.name
            else:
                raise ValueError('Cannot save %s type '%type(item)) 

def save_dict_to_hdf5(dic, h5fobj, basepath):
    '''
    Store dictionary dic into recursively defined groups,
    starting with basepath, in the h5fobj hdf5file

    load_dict_from_hdf5 and save_dict_to_hdf5 should do the same
    operations on the data in both directions to make everything
    work in native hdf5 storage types (replace / with %fs%,
    convert lists to dictionaries, convert datetime objects
    to strings, etc)
    '''

    recursively_save_dict_contents_to_group(h5fobj, basepath+'/', dic)



def load_dict_from_hdf5(h5fobj, basepath):
    ''' 
    Read the dictionary stored in hdf5obj h5file, 
    starting with basepath, into a dictionary, and
    return the resulting dictionary.

    load_dict_from_hdf5 and save_dict_to_hdf5 should do the same
    operations on the data in both directions to make everything
    work in native hdf5 storage types (replace / with %fs%, 
    convert lists to dictionaries, convert datetime objects
    to strings, etc) 
    '''

    return recursively_load_dict_contents_from_group(h5fobj, basepath+'/')
