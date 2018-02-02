integer(kind=kk), intent(in) :: nord
integer(kind=kk) :: icrs, idcr, ilow, ndon

xwrkt(1) = xdont(1)
do icrs = 2, nord
    xwrk = xdont(icrs)
    do idcr = icrs - 1, 1, - 1
        if (xwrk >= xwrkt(idcr)) exit
        xwrkt(idcr+1) = xwrkt(idcr)
    end do
    xwrkt(idcr+1) = xwrk
end do

ndon = size(xdont)
xwrk1 = xwrkt(nord)
ilow = 2*nord - ndon
do icrs = nord + 1, ndon
   if (xdont(icrs) < xwrk1) then
      xwrk = xdont(icrs)
      do idcr = nord - 1, max (1, ilow) , - 1
         if (xwrk >= xwrkt(idcr)) exit
         xwrkt(idcr+1) = xwrkt(idcr)
      end do
      xwrkt(idcr+1) = xwrk
      xwrk1 = xwrkt(nord)
   end if
   ilow = ilow + 1
end do
fndnth = xwrk1
