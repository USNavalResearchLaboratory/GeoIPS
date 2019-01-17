function solar_angle_calc,jd,lon,lat,solar_azimuth_angle=solar_azimuth_angle
    ;http://www.esrl.noaa.gov/gmd/grad/solcalc/solareqns.PDF
    debug=3
    ;# fraction year (in RADIANS)
    fraction_doy = jd-julday(1,1,fix(string(jd,format='(C(CYI4.4))')),0,0,0)
    fraction_hour = ((jd+0.5)-floor(jd+0.5))*24.0;
    ;#NOTE: DOY starts at 0.0 at the beginning of the year, not 1.0
    fraction_year = (2*!PI)*(fraction_doy/365.00) ; per source above, it's not 365.25
    ;# Don't need HH because DOY includes fractional hours,minutes,seconds
    ;# equation of time (minutes)
    eqtime = 229.18 * (0.000075+(0.001868 * cos(fraction_year)) + (-0.032077 * sin(fraction_year)) + $
                       ( -0.014615 * cos(2.0 * fraction_year)) + ( -0.040849 * sin( 2.0 * fraction_year)))
    ;# solar declination (in radians)
    decl = 0.006918-(0.399912*cos(fraction_year))+(0.070257*sin(fraction_year))-(0.006758*cos(2*fraction_year)) + $
        (0.000907*sin(2*fraction_year))-(0.002697*cos(3*fraction_year))+(0.00148*sin(3*fraction_year));
    ;# time offset (in minutes)
    time_offset = eqtime+(4*lon); 
    ;#true_solar_time (MINUTES)
    true_solar_time = (fraction_hour*60.0)+time_offset;
    ;#solar hour angle (degrees)
    hour_angle = (true_solar_time/4.0)-180;
    ;# now get solar angles
    solar_zenith_angle = (1/!DTOR)*acos((sin(!DTOR*lat)*sin(decl))+(cos(!DTOR*lat)*cos(decl)*cos(!DTOR*hour_angle)));
    solar_azimuth_inter = (((sin(!DTOR*lat)*cos(!DTOR*solar_zenith_angle))-sin(decl)) / $
                               (cos(!DTOR*lat)*sin(!DTOR*solar_zenith_angle))) ;
    solar_azimuth_angle = -((180 - ((1/!DTOR)*acos(solar_azimuth_inter))));
    ;# because of the derivation, this is -ABS(AZIMUTH). To get azimuth,
    ;we must check the sign:
    ;if(hour_angle lt 0) then solar_azimuth_angle = -solar_azimuth_angle
    ;note that HOUR_ANGLE can go past [-180,180]
    solar_azimuth_angle -= 2* solar_azimuth_angle * (sin(hour_angle*!DTOR) lt 0)
    ;print,foo
    
    ; This answer is good for the sunlit Earth. 
    
    
    
    if(debug gt 2) then print,solar_zenith_angle,solar_azimuth_angle, $
        format='("Solar Zenith (degrees) = ",f9.3,"    ' + $
        'Solar Azimuth (degrees clockwise from North) = ",f9.3)'
    return,solar_zenith_angle

end
