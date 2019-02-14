import numpy as np
import logging
import math
log = logging.getLogger(__name__)

def kts_to_ms(speed_kts):
    # To convert to ms, multiply by 0.51444
    return speed_kts * (0.51444)

def ms_to_kts(speed_ms):
    # To convert to knots, divide by 0.51444
    #return speed_ms * (463.0 / 900.0)
    return speed_ms / (0.51444)

def xy2spd(x_m, y_m, td_sec):
    # Movement is now found in terms of meters
    # Divide by the time difference (seconds) to get the speed (m/sec)

    # x,y from top right corner of image
    # so x positive to right, y positive down
    # u positive to right, v positive up

    # Positive v is wind blowing TO THE NORTH (positive y)
    v_ms = -1.0 * y_m / td_sec
    # Positive u is wind blowing TO THE EAST (positive x)
    u_ms = 1.0 * x_m / td_sec

    speed_ms, direction_deg = uv2spd(u_ms,v_ms)
    return u_ms, v_ms, speed_ms, direction_deg

def spd2uv(speed, direction_deg):
    # Positive u is wind blowing TO THE EAST (positive x)
    # Direction 0 is NORTH
    u = -1.0 * speed * np.sin(np.radians(direction_deg))
    # Positive v is wind blowing TO THE NORTH (positive y)
    # Direction 0 is NORTH
    v = -1.0 * speed * np.cos(np.radians(direction_deg))
    return u, v

def uv2spd(u, v):

    # Convert the u&v speeds to total speed
    speed = np.ma.sqrt(np.square(u) + np.square(v))

    # Find the angle of the direction (direction wind is blowing) in degrees

    # Positive u is wind blowing TO THE EAST (positive x)
    # Positive v is wind blowing TO THE NORTH (positive y)
    # Direction 0 is NORTH, -180 to 180
    direction_deg = np.ma.arctan2(-u, -v) * 180.0 / np.pi # with respect to NORTH
    #direction_deg = np.ma.mod(dire + 360.0, 360.0) # make dir positive

    #vless0 = np.ma.less(v,0)
    #vgrtr0 = np.ma.greater(v,0)
    #uless0 = np.ma.less(u,0)
    #ugrtr0 = np.ma.greater(u,0)
    #ueq0 = np.ma.equal(u,0)
    #veq0 = np.ma.equal(v,0)
    #
    #direction = np.ma.masked_array(np.ma.zeros(u.shape), mask=u.mask)
    #direction = np.ma.where(ueq0&vless0,0,direction)
    #direction = np.ma.where(veq0&uless0,90,direction)
    #direction = np.ma.where(ueq0&vgrtr0,180,direction)
    #direction = np.ma.where(veq0&ugrtr0,270,direction)
    #direction = np.ma.where(vless0&uless0,np.rad2deg(np.ma.arcsin(abs(u)/speed)),direction)
    #direction = np.ma.where(uless0&vgrtr0,np.rad2deg(np.ma.arcsin(abs(v)/speed))+90,direction)
    #direction = np.ma.where(ugrtr0&vgrtr0,np.rad2deg(np.ma.arcsin(abs(u)/speed))+180,direction)
    #direction = np.ma.where(ugrtr0&vless0,np.rad2deg(np.ma.arcsin(abs(v)/speed))+270,direction)

    return speed, direction_deg


# def get_pressure_levels(pres, arrays, pressure_cutoffs=[0,400,600,800,950,1014], returnInds = False, overlap = None):
def get_pressure_levels(pres, arrays, pressure_cutoffs=[0, 400, 800, 1014], returnInds=False, overlap=None):
    try:
        log.info('Returning values within levels %s from array with min %0.2f and max %0.2f',
                 pressure_cutoffs,
                 pres.min(),
                 pres.max(),)

    except ValueError:
        log.info('No values within levels %s from %s', pressure_cutoffs, pres)

    levArrays = []
    for arrInd in range(len(arrays)):
        currArr = arrays[arrInd]
        # If we're not just returning a list of indices, we must return a list of a list of arrays
        if returnInds == False:
            levArrays += [[]]
        for presCutoffInd in range(len(pressure_cutoffs)-1):
            pres1 = pressure_cutoffs[presCutoffInd]
            pres2 = pressure_cutoffs[presCutoffInd+1]
            if overlap is not None:
                pres1 = pres1 - overlap
                pres2 = pres2 + overlap
            inds = np.ma.where(np.ma.logical_and(pres>=pres1, pres<=pres2))
            if returnInds == True:
                levArrays += [inds] 
            else:
                levArrays[arrInd] += [currArr[inds]]  
        if returnInds == True:
            return levArrays

    return levArrays

def thin_arrays(num_points, max_points=None, arrs=[], maskInds = False):


#    if not max_points:
#        thinvalue = 5
#        #conussizex = 1500.0
#        globalrez = 10.0
#        #Size Test determines the percentage of the sector pixel size to the CONUS pixel size
#        sizetest = float((resolution)/(globalrez))
#        percenttest = sizetest*100
#        #shell()
#
#
#        if percenttest <= 75:
#            thinvalue = int((thinvalue*sizetest)+2)
#            #sizez = (sizez*sizetest)+6
#        if percenttest > 105:
#            #thinvalue = 9
#            thinvalue = int((thinvalue*sizetest)*2)
#            #sizez = 4
#            #sizez = float((sizez)/(sizetest*9))
#            #sizez = (sizez*sizetest)
#            #bold = 1
#            #bold = float((bold)/(sizetest*3))
#
#    #shell()

    if max_points == None:
        return arrs

    thinval = 1
    if num_points > max_points:
        thinval = int(num_points / max_points)
    retarrs = []


    # If we are masking the supplied indices in place within the passed arrs, 
    # thin as requested and mask the thinned values.
    if maskInds is not False:
        log.info('Masking values to thin: orig {0} points, by thin value {1} to new {2} points'.format(
                 num_points, thinval, max_points))
        maskInds = (maskInds[0][0:num_points:thinval],maskInds[1][0:num_points:thinval])
        for arr in arrs:
            log.info('        Number unmasked before thinning {1}: {0}'.format(np.ma.count(arr), arr.name))
            arr.mask = True
            arr.mask[maskInds] = False
            log.info('        Number unmasked after thinning {1}: {0}'.format(np.ma.count(arr), arr.name))
        return arrs

    # Only want to return original array if maskInds was not passed
    if thinval == 1:
        return arrs

    # If we are returning a smaller array, thin and return smaller arrays
    try:
        for arr in arrs:
            newthinval = int(math.sqrt(thinval))
            log.info('Thinning 2D array {3}: orig {0} points, by thin value {1} to new {2} points'.format(
                     num_points, newthinval, max_points, arr.name))
            retarrs += [arr[::newthinval, ::newthinval]]
			
    except IndexError:
        for arr in arrs:
            log.info('Thinning 2D array {3}: orig {0} points, by thin value {1} to new {2} points'.format(
                     num_points, thinval, max_points, arr.name))
            retarrs += [arr[::thinval]]

    return retarrs
