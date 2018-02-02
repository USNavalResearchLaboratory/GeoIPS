integer(kind=kk), dimension (:), intent (out) :: irngt

integer(kind=kk), dimension (:), allocatable :: jwrkt
integer(kind=kk) :: lmtna, lmtnc
integer(kind=kk) :: nval, iind, iwrkd, iwrk, iwrkf, jinda, iinda, iindb

nval = min (size(xvalt), size(irngt))
if (nval <= 0) then
    return
end if
!
!  Fill-in the index array, creating ordered couples
!
do iind = 2, nval, 2
    if (xvalt(iind-1) <= xvalt(iind)) then
        irngt (iind-1) = iind - 1
        irngt (iind) = iind
    else
        irngt (iind-1) = iind
        irngt (iind) = iind - 1
    end if
end do
if (modulo (nval, 2) /= 0) then
    irngt (nval) = nval
end if
!
!  We will now have ordered subsets A - B - A - B - ...
!  and merge A and B couples into     C   -   C   - ...
!
allocate (jwrkt(1:nval))
lmtnc = 2
lmtna = 2
!
!  Iteration. Each time, the length of the ordered subsets
!  is doubled.
!
do
    if (lmtna >= nval) exit
    iwrkf = 0
    lmtnc = 2 * lmtnc
    iwrk = 0

    !   Loop on merges of A and B into C
    do
        iinda = iwrkf
        iwrkd = iwrkf + 1
        iwrkf = iinda + lmtnc
        jinda = iinda + lmtna
        if (iwrkf >= nval) then
            if (jinda >= nval) exit
            iwrkf = nval
        end if
        iindb = jinda

        !   Shortcut for the case when the max of A is smaller
        !   than the min of B (no need to do anything)
        if (xvalt(irngt(jinda)) <= xvalt(irngt(jinda+1))) then
            iwrk = iwrkf
            cycle
        end if

        !  One steps in the C subset, that we create in the final rank array
        do
            if (iwrk >= iwrkf) then

                !  Make a copy of the rank array for next iteration
                irngt (iwrkd:iwrkf) = jwrkt (iwrkd:iwrkf)
                exit
            end if

            iwrk = iwrk + 1

            !  We still have unprocessed values in both A and B
            if (iinda < jinda) then
                if (iindb < iwrkf) then
                    if (xvalt(irngt(iinda+1)) > xvalt(irngt(iindb+1))) then
                        iindb = iindb + 1
                        jwrkt (iwrk) = irngt (iindb)
                    else
                        iinda = iinda + 1
                        jwrkt (iwrk) = irngt (iinda)
                    end if
                else

                    !  Only A still with unprocessed values
                    iinda = iinda + 1
                    jwrkt (iwrk) = irngt (iinda)
                end if
            else

                !  Only B still with unprocessed values
                irngt (iwrkd:iindb) = jwrkt (iwrkd:iindb)
                iwrk = iwrkf
                exit
            end if

        end do
    end do

    !  The Cs become As and Bs
    lmtna = 2 * lmtna
end do

!  Clean up
Deallocate (JWRKT)
Return
