! Author:
!    Naval Research Laboratory, Marine Meteorology Division
!
! This program is free software: you can redistribute it and/or modify it under
! the terms of the NRLMMD License included with this program.  If you did not
! receive the license, see http://www.nrlmry.navy.mil/geoips for more
! information.
!
! This program is distributed WITHOUT ANY WARRANTY; without even the implied
! warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
! included license for more details.

subroutine stddev_kernel(lines, samples, datin, wlines, wsamples, mask, datout)
    use config
    implicit none
    integer, parameter :: bd = 8
    !***************************************************************
    ! inputs
    !***************************************************************
    ! Dataset dimensions
    integer(bd), intent(in)  :: lines
    integer(bd), intent(in)  :: samples
    ! Window dimensions
    integer(bd), intent(in)  :: wlines
    integer(bd), intent(in)  :: wsamples
    ! Input dataset
    real(bd), dimension(lines, samples), intent(in) :: datin
    ! Data mask
    logical, dimension(lines, samples), optional, intent(in) :: mask
    !***************************************************************
    ! Internal Variables
    !***************************************************************
    logical, dimension(lines, samples) :: datmask
    integer(bd)  :: xind
    integer(bd)  :: xmin
    integer(bd)  :: xmax
    integer(bd)  :: yind
    integer(bd)  :: ymin
    integer(bd)  :: ymax
    integer(bd)  :: dx
    integer(bd)  :: dy
    integer(bd)  :: numgood
    real(bd)     :: boxsum
    real(bd)     :: boxmean
    !***************************************************************
    ! OUTPUT
    !***************************************************************
    ! Output dataset
    real(kind=8), intent(out) :: datout(lines, samples)

    !***************************************************************
    ! f2py Signature Information
    !***************************************************************
    !f2py integer(bd), intent(in) :: lines
    !f2py integer(bd), intent(in) :: samples
    !f2py integer(bd), intent(in) :: wlines
    !f2py integer(bd), intent(in) :: wsamples
    !f2py logical, optional, intent(in) :: mask(lines, samples)
    !f2py real(bd), intent(in) :: datin(lines, samples)
    !f2py real(bd), intent(out) :: datout(lines, samples)

    !***************************************************************
    ! test inputs
    !***************************************************************
    ! wlines must be odd
    if (mod(wlines, 2) == 0) then
        stop 1001
    endif
    ! wsamples must be odd
    if (mod(wsamples, 2) == 0) then
        stop 1002
    endif

    if (present(mask)) datmask = mask
    datout(1,1) = 0.0

    !***************************************************************
    ! start routine
    !***************************************************************
    ! Set up internal constants
    dx = (wlines - 1)/2
    dy = (wsamples - 1)/2
    ! Loop over input array
    do xind = 1, lines
        xmin = xind - dx
        xmax = xind + dx
        if (xmin < 1) xmin = 1
        if (xmax > lines) xmax = lines
        do yind = 1, samples
            !If this datapoint is masked, then set stddev to zero
            if (datmask(xind, yind) .eqv. .TRUE.) then
                datout(xind, yind) = 0
                cycle
            endif
            ymin = yind - dy
            ymax = yind + dy
            if (ymin < 1) ymin = 1
            if (ymax > samples) ymax = samples

            !Determine number of good samples
            numgood = (xmax-xmin+1)*(ymax-ymin+1) - count(datmask(xmin:xmax, ymin:ymax))
            !Sum the good elements of the box
            boxsum = sum(datin(xmin:xmax, ymin:ymax), mask=datmask(xmin:xmax, ymin:ymax).eqv..FALSE.)
            !Get the mean of the good elements of the box
            boxmean = boxsum/numgood
            !Get the standard deviation of the box
            datout(xind, yind) = sqrt(sum(datin(xmin:xmax, ymin:ymax)**2,&
                                          mask=datmask(xmin:xmax, ymin:ymax).eqv..FALSE.&
                                     )/numgood - boxmean**2)
        enddo
    enddo

end subroutine stddev_kernel

