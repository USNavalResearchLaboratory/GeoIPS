integer(kind=kk), intent(out) :: indm
integer(kind=kk) :: idon
integer(kind=kk), dimension(size(xdont)) :: idont

idont = (/(idon, idon=1, size(xdont))/)
