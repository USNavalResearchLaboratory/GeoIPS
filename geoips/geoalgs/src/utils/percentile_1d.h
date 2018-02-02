logical, optional,    intent(in)    :: mask(:)
!If mask was passed, then only look at unmasked values
if (present(mask)) then
    ngood = count(mask)
    allocate(tempitem(ngood))
    tind = 1
    do aind = 1, size(item)
        if (mask(aind)) then
            tempitem(tind) = item(aind)
            tind = tind + 1
        end if
    end do
else
    ngood = size(item)
    allocate(tempitem(ngood))
    tempitem = item
end if

!Sort the array
allocate(ranks(ngood))
call mrgrnk(tempitem, ranks)

!Find the appropriate indecies
inds = ceiling((percs/100.0) * ngood)
where (inds == 0) inds = 1
vals = tempitem(ranks(inds))
print *, 'vals:',vals
deallocate(tempitem)
deallocate(ranks)
