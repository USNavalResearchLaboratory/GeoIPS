real(kk), intent(in) :: val
real(kk), intent(in) :: vmin, vmax
logical, optional, intent(in) :: doclip
real(kk) :: clip_vmin, clip_vmax
real(kk) :: ret

clip_vmin = 0.0
clip_vmax = 1.0

ret = (val - vmin)/(vmax - vmin)

if (present(doclip) .and. doclip) then
    ret = clip(ret, clip_vmin, clip_vmax)
endif
