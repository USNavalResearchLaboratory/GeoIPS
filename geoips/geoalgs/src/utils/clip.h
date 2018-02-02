if (val .lt. vmin) then
    ret = vmin
else if (val .gt. vmax) then
    ret = vmax
else
    ret = val
endif
