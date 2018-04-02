from datetime import datetime
import h5py
import numpy as np
from IPython import embed as shell

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
                # Turn string datetime back into datetime obj
                try:
                    ans[key] = datetime.strptime(ans[key], '%Y%m%d%H%M%S.%f')
                except:
                    pass
            # These should work as straight hdf5 variable types
            elif isinstance(item,.value, (np.ndarray, np.int64, np.float64, bytes)):
                ans[key] = item.value 
            elif isinstance(item.value, (np.float32, np.int32, int, np.uint64)):
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
                ans[key] = recursively_load_dict_contents_from_group(h5file, path+pathkey+'/'_
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
            raise ValueError('Cannot save %s type '%type(item)) 

def save_dict_to_hdf5(dic, h5fobj, basepath):
''' Store dictionary dic into recursively defined groups,
    starting with basepath, in the h5fobj hdf5file
    
load_dict_from_hdf5 and save_dict_to_hdf5 should do the same
    operations on the data in both directions to make everything
    work in native hdf5 storage types (replace / with %fs%, 
    convert lists to dictionaries, convert datetime objects
    to strings, etc) '''

    recursively_save_dict_contents_to_group(h5fobj, basepath+'/', dic)



def load_dict_from_hdf5(h5fobj, basepath):
''' Read the dictionary stored in hdf5obj h5file, 
    starting with basepath, into a dictionary, and
    return the resulting dictionary.

load_dict_from_hdf5 and save_dict_to_hdf5 should do the same
    operations on the data in both directions to make everything
    work in native hdf5 storage types (replace / with %fs%, 
    convert lists to dictionaries, convert datetime objects
    to strings, etc) '''

    return recursively_load_dict_contents_from_group(h5fobj, basepath+'/')
