!
! This code was borrowed from the "orderpack" package.
! It was ripped out into an include file to allow easy interface
!   development
real(kind=kk), intent(in) :: pcls
real(kind=kk), dimension(size(xdont)) :: xindt
integer(kind=kk), dimension(size(xdont)) :: jwrkt
real(kind=kk) :: pwrk
integer(kind=kk) :: i

call random_number(xindt(:))
pwrk = min(max(0.0, pcls), 1.0)
xindt = real(size(xdont)) * xindt
xindt = pwrk * xindt + (1.0 - pwrk) * (/ (real(i), i=1, size(xdont)) /)
call mrgrnk(xindt, jwrkt)
xdont  = xdont(jwrkt)
