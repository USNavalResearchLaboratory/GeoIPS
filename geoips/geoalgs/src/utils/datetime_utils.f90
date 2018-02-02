module datetime_utils

    use config

    implicit none

    integer, parameter, private :: bd = 8

    type :: Date_Time
        character(len=20) :: datetime
        character(len=4) :: year
        character(len=2) :: month
        character(len=2) :: day
        character(len=2) :: hour
        character(len=2) :: minute
        character(len=2) :: second
        character(len=3) :: doy
        integer(bd) :: i_year
        integer(bd) :: i_month
        integer(bd) :: i_day
        integer(bd) :: i_hour
        integer(bd) :: i_minute
        integer(bd) :: i_second
        integer(bd) :: i_doy
    end type Date_Time

    contains

    logical function is_leap_year(year)
        ! If the year is a leap year, returns .true.
        ! Otherwise returns .false.
        implicit none
        integer(bd), intent(in) :: year

        if (mod(year, 4) .eq. 0) then
            ! If divisable by 4, but not by 100, then leap year
            if (mod(year, 100) .ne. 0) then
                is_leap_year = .true.
            ! If divisable by 100
            else
                ! If divisible by 400, then leap, otherwise not
                if (mod(year, 400) .eq. 0) then
                    is_leap_year = .true.
                else
                    is_leap_year = .false.
                endif
            endif
        else
            is_leap_year = .false.
        endif
    end function is_leap_year

    subroutine days_in_month(year, month, days, code)
        ! Gets the number of days in the input month for the specific year.
        ! Handles leap years.
        use errors
        implicit none
        integer(bd), intent(in) :: year
        integer(bd), intent(in) :: month
        integer(bd), dimension(12) :: n_days = (/ 31, 28, 31, 30, 31, 30, 31, &
                                            31, 30, 31, 30, 31 /)
        logical :: is_leap
        integer(bd), intent(out) :: days
        integer(bd), intent(out) :: code
        code = 0

        ! Test input month
        if ((month .lt. 1) .or. (month .gt. 12)) then
            call Date_TimeError('Month out of range [1, 12].', code)
            return
        endif

        ! Get number of days
        is_leap = is_leap_year(year)
        days = n_days(month)
        if (month .eq. 2) then
            if (is_leap) then
                days = 29
            else
                days = 28
            endif
        endif
    end subroutine days_in_month

    subroutine day_of_year(year, month, day, doy, code)
        ! Calculate day of year from year, month, and day of month
        use errors
        implicit none
        integer(bd), intent(in) :: year
        integer(bd), intent(in) :: month
        integer(bd), intent(in) :: day
        integer(bd) :: mdays, mind
        integer(bd), intent(out) :: doy
        integer(bd), intent(out) :: code

        ! Initialize
        doy = 0
        code = 0

        ! Loop over months until current month and sum number of days
        do mind=1, month-1
            call days_in_month(year, mind, mdays, code)
            if (code .ne. 0) then
                return
            endif
            doy = doy + mdays
        enddo
        ! Add the days from the current month
        doy = doy + day

        ! Just checking
        if (doy .gt. 366) then
            call Date_TimeError('Calculated day of year greater than 366.', doy, code)
            return
        endif
    end subroutine day_of_year

    subroutine test_second(second, code)
        ! Test that second is in the range [0, 60)
        use errors
        implicit none
        integer(bd), intent(in) :: second
        integer(bd), intent(out) :: code
        code = 0

        if ((second .lt. 0) .or. (second .gt. 59)) then
            call Date_TimeError('Second is out of range [0, 60)', second, code)
        endif
    end subroutine

    subroutine test_minute(minute, code)
        ! Test that hour is in the range [0, 24)
        use errors
        implicit none
        integer(bd), intent(in) :: minute
        integer(bd), intent(out) :: code
        code = 0

        if ((minute .lt. 0) .or. (minute .gt. 59)) then
            call Date_TimeError('Minute is out of range [0, 60)', minute, code)
        endif
    end subroutine

    subroutine test_hour(hour, code)
        ! Test that hour is in the range [0, 24)
        use errors
        implicit none
        integer(bd), intent(in) :: hour
        integer(bd), intent(out) :: code
        code = 0

        if ((hour .lt. 0) .or. (hour .gt. 23)) then
            call Date_TimeError('Hour is out of range [0, 24)', hour, code)
        endif
    end subroutine

    subroutine test_day_of_month(year, month, day, code)
        ! Test that the day of month falls in the appropriate range
        use errors
        implicit none
        integer(bd), intent(in) :: year, month, day
        integer(bd) :: max_days
        integer(bd), intent(out) :: code
        code = 0

        call days_in_month(year, month, max_days, code)
        if ((day .lt. 1) .or. (day .gt. max_days)) then
            call Date_TimeError('Day out of range for given month.', day, code)
        endif
    end subroutine test_day_of_month

    subroutine test_month(month, code)
        ! Test that month is in the range [1, 12]
        use errors
        implicit none
        integer(bd), intent(in) :: month
        integer(bd), intent(out) :: code
        code = 0

        if ((month .lt. 1) .or. (month .gt. 12)) then
            call Date_TimeError('Month out of range [1, 12]', month, code)
        endif
    end subroutine test_month

    subroutine test_datetime(dt, code)
        use errors
        implicit none
        type(Date_Time), intent(in) :: dt
        integer(bd), intent(out) :: code
        code = 0

        ! Test inputs
        call test_month(dt%i_month, code)
        if (code .ne. 0) then
            return
        endif

        call test_day_of_month(dt%i_year, dt%i_month, dt%i_day, code)
        if (code .ne. 0) then
            return
        endif

        call test_hour(dt%i_hour, code)
        if (code .ne. 0) then
            return
        endif

        call test_minute(dt%i_minute, code)
        if (code .ne. 0) then
            return
        endif

        call test_second(dt%i_second, code)
        if (code .ne. 0) then
            return
        endif

    end subroutine test_datetime

    subroutine datetime_to_str(in_dt, out_dt, code)
        implicit none
        ! Accepts a datetime object as created by datetime_from_str and returns
        ! a timstamp in the form YYYY-MM-DDTHH:MM:DDZ.
        type(Date_Time), intent(in) :: in_dt
        character(len=20), intent(out) :: out_dt
        integer(bd), intent(out) :: code
        code = 0

        ! Test the instance to be sure it's a good one
        call test_datetime(in_dt, code)
        if (code .ne. 0) then
            return
        endif

        ! Construct the string
        out_dt = in_dt%year // '-' // in_dt%month // '-' // in_dt%day // &
                 'T' // in_dt%hour // ':' // in_dt%minute // ':' // &
                 in_dt%second // 'Z'
    end subroutine datetime_to_str

    subroutine datetime_from_fields(year, month, day, hour, minute, second, &
                                    out_dt, code)
        ! Accepts integers for year, month, day, hour, minute, and second and
        ! returns a Date_Time type object.  This object contains the year, month,
        ! day, hour, minute, and second as separate fields.  Additionally,
        ! i_year, i_month, i_day, i_hour, i_minute, and i_second contain integer
        ! values for each field.
        use errors
        implicit none
        integer(bd), intent(in) :: year, month, day, hour, minute, second
        integer(bd) :: doy
        character(len=20) :: s_datetime
        character(len=4) :: s_year
        character(len=3) :: s_doy
        character(len=2) :: s_month, s_day, s_hour, s_minute, s_second
        integer(bd) :: stat
        ! integer(bd) :: max_days
        ! logical :: is_leap
        type(Date_Time), intent(out) :: out_dt
        integer(bd), intent(out) :: code
        code = 0

        ! Convert to strings
        write(s_year, '(I4.4)', iostat=stat) year
        if (stat .ne. 0) then
            call Date_TimeError('Incorrect format for year.', s_year, code)
            return
        endif
        write(s_month, '(I2.2)', iostat=stat) month
        if (stat .ne. 0) then
            call Date_TimeError('Incorrect format for month.', s_month, code)
            return
        endif
        write(s_day, '(I2.2)', iostat=stat) day
        if (stat .ne. 0) then
            call Date_TimeError('Incorrect format for day.', s_day, code)
            return
        endif
        write(s_hour, '(I2.2)', iostat=stat) hour
        if (stat .ne. 0) then
            call Date_TimeError('Incorrect format for hour.', s_hour, code)
            return
        endif
        write(s_minute, '(I2.2)', iostat=stat) minute
        if (stat .ne. 0) then
            call Date_TimeError('Incorrect format for minute.', s_minute, code)
            return
        endif
        write(s_second, '(I2.2)', iostat=stat) second
        if (stat .ne. 0) then
            call Date_TimeError('Incorrect format for second.', s_second, code)
            return
        endif
        s_datetime = s_year // '-' // s_month // '-' // s_day // 'T' // s_hour // ':' // &
            s_minute // ':' // s_second // 'Z'

        ! Calculate day of year
        call day_of_year(year, month, day, doy, code)
        if (code .ne. 0) then
            return
        endif
        print *, doy
        write(s_doy, '(I3.3)', iostat=stat) doy
        if (stat .ne. 0) then
            call Date_TimeError('Failed to convert day of year to string.', s_doy, code)
            return
        endif

        ! Add strings to object
        out_dt%year = s_year
        out_dt%month = s_month
        out_dt%day = s_day
        out_dt%hour = s_hour
        out_dt%minute = s_minute
        out_dt%second = s_second
        out_dt%doy = s_doy
        out_dt%datetime = s_datetime

        ! Add integers to object
        out_dt%i_year = year
        out_dt%i_month = month
        out_dt%i_day = day
        out_dt%i_hour = hour
        out_dt%i_minute = minute
        out_dt%i_second = second
        out_dt%i_doy = doy

        call test_datetime(out_dt, code)

    end subroutine datetime_from_fields

    subroutine datetime_from_str(in_dt, out_dt, code)
        ! Accepts a timestamp in the form YYYY-MM-DDTHH:MM:SSZ and returns a
        ! Date_Time type object.  This object contains the year, month, day, 
        ! hour, minute, and second as separate fields.  Additionally, i_year,
        ! i_month, i_day, i_hour, i_minute, and i_second contain integer values
        ! for each field.
        use errors
        implicit none
        character(len=20), intent(in) :: in_dt
        character(len=4) :: year
        character(len=2) :: month, day, hour, minute, second
        integer(bd) :: i_year, i_month, i_day, i_hour, i_minute, i_second ! , max_days
        ! logical :: is_leap
        integer(bd) :: stat
        type(Date_Time), intent(out) :: out_dt
        integer(bd), intent(out) :: code
        code = 0

        ! Test input string
        if (len_trim(in_dt) .ne. 20) then
            call Date_TimeError('Input string must be 20 characters long ' // &
                               ' with no spaces in the form ' // &
                               'YYYY-MM-DDTHH:MM:SSZ.', code)
            return
        endif

        ! Get parts
        year = in_dt(1:4)
        month = in_dt(6:7)
        day = in_dt(9:10)
        hour = in_dt(12:13)
        minute = in_dt(15:16)
        second = in_dt(18:19)

        ! Convert to integers
        read(year, '(I4.4)', iostat=stat) i_year
        if (stat .ne. 0) then
            call Date_TimeError('Incorrect format for year.', year, code)
            return
        endif
        read(month, '(I2.2)', iostat=stat) i_month
        if (stat .ne. 0) then
            call Date_TimeError('Incorrect format for month.', month, code)
            return
        endif
        read(day, '(I2.2)', iostat=stat) i_day
        if (stat .ne. 0) then
            call Date_TimeError('Incorrect format for day.', day, code)
            return
        endif
        read(hour, '(I2.2)', iostat=stat) i_hour
        if (stat .ne. 0) then
            call Date_TimeError('Incorrect format for hour.', hour, code)
            return
        endif
        read(minute, '(I2.2)', iostat=stat) i_minute
        if (stat .ne. 0) then
            call Date_TimeError('Incorrect format for minute.', minute, code)
            return
        endif
        read(second, '(I2.2)', iostat=stat) i_second
        if (stat .ne. 0) then
            call Date_TimeError('Incorrect format for second.', second, code)
            return
        endif

        call datetime_from_fields(i_year, i_month, i_day, i_hour, i_minute, &
                                  i_second, out_dt, code)
    end subroutine

end module datetime_utils
