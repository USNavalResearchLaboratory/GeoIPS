integer, intent(out) :: nuni

integer, dimension(size(xdont)) :: iwrkt
logical, dimension(size(xdont)) :: ifmptyt
integer :: icrs

call uniinv(xdont, iwrkt)
ifmptyt = .true.
nuni = 0
do icrs = 1, size(xdont)
    if (ifmptyt(iwrkt(icrs))) then
        ifmptyt(iwrkt(icrs)) = .false.
        nuni = nuni + 1
        xdont(nuni) = xdont(icrs)
    end if
end do
return
