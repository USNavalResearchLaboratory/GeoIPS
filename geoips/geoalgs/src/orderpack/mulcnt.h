integer(kind=kk), dimension(:), intent(out) :: imult
integer(kind=kk), dimension(size(xdont)) :: iwrkt
integer(kind=kk), dimension(size(xdont)) :: icntt
integer(kind=kk) :: icrs

call uniinv(xdont, iwrkt)
icntt = 0
do icrs = 1, size(xdont)
      icntt(iwrkt(icrs)) = icntt(iwrkt(icrs)) + 1
end do
do icrs = 1, size(xdont)
      imult(icrs) = icntt(iwrkt(icrs))
end do
