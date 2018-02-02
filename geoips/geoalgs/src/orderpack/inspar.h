integer(kind=kk), intent(in) :: nord
integer(kind=kk) :: icrs, idcr

do icrs = 2, nord
    xwrk = xdont(icrs)
    do idcr = icrs - 1, 1, - 1
        if (xwrk >= xdont(idcr)) exit
        xdont(idcr+1) = xdont(idcr)
    end do
    xdont(idcr+1) = xwrk
end do

xwrk1 = xdont(nord)
do icrs = nord + 1, size(xdont)
    if (xdont(icrs) < xwrk1) then
        xwrk = xdont(icrs)
        xdont(icrs) = xwrk1
        do idcr = nord - 1, 1, - 1
            if (xwrk >= xdont(idcr)) exit
            xdont (idcr+1) = xdont(idcr)
        end do
        xdont(idcr+1) = xwrk
        xwrk1 = xdont(nord)
    end if
end do
