program test_datetime_utils

    use datetime_utils

    implicit none

    character(len=20), dimension(10) :: dt_str
    character(len=4), dimension(10) :: expected
    type(DateTime) :: dt_obj
    integer :: int_ret, n_failed, code, days, month, year, strind

    n_failed = 0

    !******************************
    ! Test is_leap_year
    !******************************
    print *, 'Testing is_leap_year function'
    print *, '    Testing non-leap year (2015)'
    if (is_leap_year(2015)) then
        print *, '    Failed to identify 2015 as non-leap year.'
        n_failed = n_failed + 1
    else
        print *, '    Passed'
    endif
    print *, '    Testing leap year (2016)'
    if (is_leap_year(2016)) then
        print *, '    Passed'
    else
        print *, '    Failed to identify 2016 as leap year.'
        n_failed = n_failed + 1
    endif
    print *, '    Testing non-leap year (1900)'
    if (is_leap_year(1900)) then
        print *, '    Failed to identify 1900 as non-leap year.'
        n_failed = n_failed + 1
    else
        print *, '    Passed'
    endif
    print *, '    Testing leap year (2000)'
    if (is_leap_year(2000)) then
        print *, '    Passed'
    else
        print *, '    Failed to identify 2000 as leap year.'
        n_failed = n_failed + 1
    endif
    !******************************

    !******************************
    ! Test days in month subroutine
    !   Just testing last day of Feb
    !   All else will work if Feb works
    !******************************
    print *, ''
    print *, 'Testing days_in_month function'
    call days_in_month(2015, 2, int_ret, code)
    if (code .ne. 0) then
        print *, '    Failed due to error.'
        n_failed = n_failed + 1
    else if (int_ret .ne. 28) then
        print *, '    Failed on Feb, 2015.  Wanted 28.  Got: ', int_ret
        n_failed = n_failed + 1
    else
        print *, '    Passed'
    endif
    call days_in_month(2016, 2, int_ret, code)
    if (code .ne. 0) then
        print *, '    Failed due to error.'
        n_failed = n_failed + 1
    else if (int_ret .ne. 29) then
        print *, '    Failed on Feb, 2016.  Wanted 29.  Got: ', int_ret
        n_failed = n_failed + 1
    else
        print *, '    Passed'
    endif
    !******************************

    !******************************
    ! Test day of year
    !******************************
    print *, ''
    print *, 'Testing day_of_year function'
    call day_of_year(2015, 2, 28, int_ret, code)
    if (code .ne. 0) then
        print *, '    Failed due to error.'
        n_failed = n_failed + 1
    else if (int_ret .ne. 59) then
        print *, '    Failed on Feb 28th, 2015.  Wanted 59.  Got: ', int_ret
        n_failed = n_failed + 1
    else
        print *, '    Passed'
    endif
    call day_of_year(2015, 2, 29, int_ret, code)
    if (code .ne. 0) then
        print *, '    Passed'
    else
        print *, '    Failed on Feb 29th, 2015.  Should have raised error.'
        n_failed = n_failed + 1
    endif
    call day_of_year(2016, 2, 29, int_ret, code)
    if (code .ne. 0) then
        print *, '    Failed due to error.'
        n_failed = n_failed + 1
    else if (int_ret .ne. 60) then
        print *, '    Failed on Feb 29th, 2016.  Wanted 60.  Got: ', int_ret
        n_failed = n_failed + 1
    else
        print *, '    Passed'
    endif
    call day_of_year(2015, 12, 31, int_ret, code)
    if (code .ne. 0) then
        print *, '    Failed due to error.'
        n_failed = n_failed + 1
    else if (int_ret .ne. 365) then
        print *, '    Failed on Dec 31st, 2015.  Wanted 365.  Got: ', int_ret
        n_failed = n_failed + 1
    else
        print *, '    Passed'
    endif
    call day_of_year(2016, 12, 31, int_ret, code)
    if (code .ne. 0) then
        print *, '    Failed due to error.'
        n_failed = n_failed + 1
    else if (int_ret .ne. 366) then
        print *, '    Failed on Dec 31st, 2016.  Wanted 366.  Got: ', int_ret
        n_failed = n_failed + 1
    else
        print *, '    Passed'
    endif
    !******************************

    dt_str = (/ '2016-11-22T16:06:15Z', & ! good
                '4352-13-01T00:00:00Z', & ! month too high
                '2015-12-01T00:00:00Z', & ! good
                '2016-02-29T00:00:00Z', & ! good leap year on 2/29
                '2015-02-29T00:00:00Z', & ! bad non-leap year on 2/29
                '2015-02-28T00:00:00Z', & ! good non-leap year on 2/28
                '234-01-01T00:00:00Z ', & ! bad short year left justified
                '2015-1-01T00:00:00Z ', & ! bad short month (covers all others)
                ' 234-01-01T00:00:00Z', & ! good short year right justified
                ' 2015-1-01T00:00:00Z'  & ! bad short month (covers all others)
            /)
    expected = (/ 'pass', &
                  'fail', &
                  'pass', &
                  'pass', &
                  'fail', &
                  'pass', &
                  'fail', &
                  'fail', &
                  'fail', &
                  'fail' &
                /)

    print *, ''
    print *, 'Testing datetime_from_str'
    do strind = 1, size(dt_str)
        print *, '    Using ' // dt_str(strind)
        call datetime_from_str(dt_str(strind), dt_obj, code)
        if (code .ne. 0) then
            if (expected(strind) .eq. 'fail') then
                print *, '    Passed'
            else
                print *, '    Failed'
                n_failed = n_failed + 1
            endif
        else
            if (expected(strind) .eq. 'pass') then
                print *, '    Passed'
            else
                print *, '    Failed'
                n_failed = n_failed + 1
            endif
            print *, 'Year:   ' // dt_obj%year
            print *, 'Month:  ' // dt_obj%month
            print *, 'Day:    ' // dt_obj%day
            print *, 'Hour:   ' // dt_obj%hour
            print *, 'Minute: ' // dt_obj%minute
            print *, 'Second: ' // dt_obj%second
            print *, 'INT: Year:   ', dt_obj%i_year
            print *, 'INT: Month:  ', dt_obj%i_month
            print *, 'INT: Day:    ', dt_obj%i_day
            print *, 'INT: Hour:   ', dt_obj%i_hour
            print *, 'INT: Minute: ', dt_obj%i_minute
            print *, 'INT: Second: ', dt_obj%i_second
        endif
    enddo

    print *, ''
    print *, 'Completed tests with ', n_failed, ' failures'
end program test_datetime_utils

