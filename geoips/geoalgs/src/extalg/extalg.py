#!/bin/env python
import os

def extalg(datafile, sector, product, workdir):
    '''
    This is a template for creating an external algorithm for operating on 
    arbitrary data types from the datafile (registered, sectored, 
    pre-registered...), and returning arbitrary arrays.  There must be a 
        geoalgs/src/extalg_plot
        geoalgs/src/extalg_coverage
    to go with 
        geoalgs/src/extalg
    so the plotting and coverage checking routines know how to handle the
    arbitrary arrays. 
    This is a pretty useless function, but should hopefully provide a 
        template for more useful applications.
    '''


    '''
    This should probably go somewhere else, but here is a template for 
    saving out the SciFile object as an hdf5.

    This pre-processed file will have all datatypes that were read in
    included - navgem, abi, ahi, viirs, etc
    '''
    write_file = False
        if 'preprocessed' not in dfname:
            write_file = True
    if write_file:
        dirname = os.getenv(GEOIPS_OUTDIRS)+'/data/preprocessed/%s_%s'%(datafile.source_name,
                                            datafile.security_classification.replace('/','-'))
        baseh5filename = '%s/%s_%s'%(dirname,
                            sector.name,
                            '_'.join(sorted(datafile.datasets.keys())))
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        h5filename = baseh5filename+'.h5'
        ii = 0
        while os.path.exists(h5filename):
            h5filename = '%s_%03d%s'%(baseh5filename, ii, '.h5')
            ii+=1
        log.info('Writing out pre-sectored h5 data file: '+h5filename)


    '''
    Example if you want to register some data in here
    '''
    log.info('Registering datasets...')
    registered_data = datafile.register(sector.area_definition,
            interp_method = None,
            roi = None
            #required_datasets = ['B13BT']


    '''
    This is a ridiculous process, but calling
    extalg_config on the empty dictionary populates the 
    dictionary with the appropriate variable names.
    This should be cleaned up, but this template gives us
    a starting point for specifying different sat configs
    dynamically
    '''
    from .extalg_config import extalg_config
    sat_config = {}
    extalg_config(sat_config)


    '''
    Here is your arbitrary outdata dictionary!!!
    You can put anything you want in here !!!!
    Then tell <extalg>_plot how to plot each entry, 
    and <extalg>_coverage how to check coverage for
    each entry!!!!
    '''
    outdata = {}
    for ds in registered_data.datasets.values():
        # Grab the appropriate variable name out of the sat_config dict
        srcname = ds.source_name
        varname = sat_config[srcname]['varname']
        # now set the outdata dictionary to the appropriate data array.
        outdata[srcname+'irvar'] = ds.variables[varname]

    return outdata
