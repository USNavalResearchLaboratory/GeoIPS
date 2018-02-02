logical :: tempmask(size(item))
logical, optional, intent(in) :: mask(size(item,1),size(item,2))

!Store in a temporary array and reshape to 1d
temp = reshape(item, (/ size(item) /))

!Store mask in a temporary array and reshape to 1d
if (present(mask)) then
    tempmask = reshape(mask, (/ size(mask) /))
else
    tempmask(:) = .true.
end if
