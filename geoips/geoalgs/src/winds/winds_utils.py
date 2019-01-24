import numpy as np

def kts_to_ms(speed_kts):
    # To convert to ms, multiply by 0.51444
    return speed_kts * (0.51444)

def ms_to_kts(speed_ms):
    # To convert to knots, divide by 0.51444
    #return speed_ms * (463.0 / 900.0)
    return speed_ms / (0.51444)

def uv2spd(u, v):

    # Convert the u&v speeds to total speed
    speed = np.ma.sqrt(np.square(u) + np.square(v))

    # Find the angle of the direction (moving toward) in degrees
    #dire = np.ma.arctan2(v, u) * 180.0 / np.pi # from x-axis
    #direction = np.ma.mod(dire + 360.0, 360.0) # make dir positive

    vless0 = np.ma.less(v,0)
    vgrtr0 = np.ma.greater(v,0)
    uless0 = np.ma.less(u,0)
    ugrtr0 = np.ma.greater(u,0)
    ueq0 = np.ma.equal(u,0)
    veq0 = np.ma.equal(v,0)
    
    direction = np.ma.masked_array(np.ma.zeros(u.shape), mask=u.mask)
    direction = np.ma.where(ueq0&vless0,0,direction)
    direction = np.ma.where(veq0&uless0,90,direction)
    direction = np.ma.where(ueq0&vgrtr0,180,direction)
    direction = np.ma.where(veq0&ugrtr0,270,direction)
    direction = np.ma.where(vless0&uless0,np.rad2deg(np.ma.arcsin(abs(u)/speed)),direction)
    direction = np.ma.where(uless0&vgrtr0,np.rad2deg(np.ma.arcsin(abs(v)/speed))+90,direction)
    direction = np.ma.where(ugrtr0&vgrtr0,np.rad2deg(np.ma.arcsin(abs(u)/speed))+180,direction)
    direction = np.ma.where(ugrtr0&vless0,np.rad2deg(np.ma.arcsin(abs(v)/speed))+270,direction)

    return speed, direction

def downsample_winds(resolution, thinvalue=None, arrs=[]):


    if not thinvalue:
        thinvalue = 5
        #conussizex = 1500.0
        globalrez = 10.0
        #Size Test determines the percentage of the sector pixel size to the CONUS pixel size
        sizetest = float((resolution)/(globalrez))
        percenttest = sizetest*100
        #shell()


        if percenttest <= 75:
            thinvalue = int((thinvalue*sizetest)+2)
            #sizez = (sizez*sizetest)+6
        if percenttest > 105:
            #thinvalue = 9
            thinvalue = int((thinvalue*sizetest)*2)
            #sizez = 4
            #sizez = float((sizez)/(sizetest*9))
            #sizez = (sizez*sizetest)
            #bold = 1
            #bold = float((bold)/(sizetest*3))

    #shell()
    retarrs = []

    try:
        for arr in arrs:
            retarrs += [arr[::thinvalue,::thinvalue]]
			
    except IndexError:
        for arr in arrs:
            retarrs += [arr[::thinvalue]]

    return retarrs
