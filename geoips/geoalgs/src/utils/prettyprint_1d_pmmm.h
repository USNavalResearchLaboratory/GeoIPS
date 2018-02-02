character(*), intent(in) :: str
logical, target, optional   :: mask(size(arr, 1))
logical, target             :: true_mask(size(arr, 1))
logical, pointer            :: mask_ptr(:)

true_mask = .true.

if (present(mask)) then
    mask_ptr => mask
else
    mask_ptr => true_mask
endif

print *, str//': ', 'MIN =', minval(arr, mask=mask_ptr), &
                    'MEAN=', sum(arr, mask=mask_ptr)/(max(1,count(mask_ptr))), &
                    'MAX =', maxval(arr, mask=mask_ptr)
print *, shape(arr), count(mask_ptr)
