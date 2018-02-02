integer, dimension(:), intent(out) :: irngt
integer, intent(in) :: nord

integer :: icrs, idcr

irngt(1) = 1
do icrs=2, nord
    xwrk = xdont(icrs)
    do idcr = icrs - 1, 1, - 1
        if (xwrk >= xdont(irngt(idcr))) exit
        irngt(idcr+1) = irngt(idcr)
    end do
    irngt(idcr+1) = icrs
end do

xwrk1 = xdont(irngt(nord))
do icrs=nord+1, size(xdont)
    if (xdont(icrs) < xwrk1) then
        xwrk = xdont(icrs)
        do idcr=nord-1, 1, -1
            if (xwrk >= xdont(irngt(idcr))) exit
            irngt(idcr+1) = irngt(idcr)
        end do
        irngt(idcr+1) = icrs
        xwrk1 = xdont(irngt(nord))
    end if
end do
