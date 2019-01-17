def geo_stitched_config(sourcename):
    sat_config = {}
    sat_config['Infrared'] = { 
                          'compare_platforms' : ['goes16','himawari8','meteoIO','meteoEU'], 
                          'compare_sources' : ['abi','ahi','seviri','seviri'], 
                          'compare_channels' : {'abi': 'B14BT','ahi': 'B14BT','seviri': 'IR_120'}, 
                          'max_time_diff': 30, 
                          'data_min': 173,
                          'data_max': 323,
                          'enhance_params' : None, 
                            }


    return sat_config
