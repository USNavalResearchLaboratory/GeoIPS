integer(kind=kk) :: icrs, idcr, ndon

ndon = size (xdont)
!
! we first bring the minimum to the first location in the array.
! that way, we will have a "guard", and when looking for the
! right place to insert a value, no loop test is necessary.
!
if (xdont (1) < xdont (ndon)) then
    xmin = xdont (1)
else
    xmin = xdont (ndon)
    xdont (ndon) = xdont (1)
endif
do idcr = ndon-1, 2, -1
    xwrk = xdont(idcr)
    if (xwrk < xmin) then
        xdont (idcr) = xmin
        xmin = xwrk
    end if
end do
xdont (1) = xmin
!
! the first value is now the minimum
! loop over the array, and when a value is smaller than
! the previous one, loop down to insert it at its right place.
!
do icrs = 3, ndon
    xwrk = xdont (icrs)
    idcr = icrs - 1
    if (xwrk < xdont(idcr)) then
        xdont (icrs) = xdont (idcr)
        idcr = idcr - 1
        do
            if (xwrk >= xdont(idcr)) exit
            xdont (idcr+1) = xdont (idcr)
            idcr = idcr - 1
        end do
        xdont (idcr+1) = xwrk
    end if
end do

return
