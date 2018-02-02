module errors

    use error_codes
    use io_messages
    
    implicit none
    integer, parameter, private :: bd = 8

    interface ValueError
        module procedure n_ValueError, i_ValueError, l_ValueError, r_ValueError, &
            d_ValueError, c_ValueError
    end interface ValueError
    interface ValidRangeError
        module procedure n_ValidRangeError, i_ValidRangeError, l_ValidRangeError, r_ValidRangeError, &
                d_ValidRangeError, i_mm_ValidRangeError, r_mm_ValidRangeError, d_mm_ValidRangeError
    end interface ValidRangeError

    interface Date_TimeError
        module procedure n_Date_TimeError, i_Date_TimeError, l_Date_TimeError, &
            r_Date_TimeError, d_Date_TimeError, c_Date_TimeError
    end interface Date_TimeError
    interface IOStatusError
        module procedure i_IOStatusError, l_IOStatusError
    end interface IOStatusError

    contains

    subroutine Error(msg, code)
        character(*), intent(in) :: msg
        integer(bd), intent(out) :: code
        print *, msg
        code = 0
    end subroutine Error

    subroutine NoSuchFileError(fname, code)
        character(*), intent(in) :: fname
        integer(bd), intent(out) :: code

        print *, 'NoSuchFileError: Requested file does not exist:'
        print *, '    Recieved: ', fname
        code = NoSuchFileCode
    end subroutine NoSuchFileError

    subroutine i_IOStatusError(stat, code)
        integer, intent(in) :: stat
        character(256) :: msg
        integer(bd), intent(out) :: code
        call retrieve_io_error_message(stat, msg)
        print *, 'IOStatusError: ', stat,  msg
        code = IOStatusErrorCode
    end subroutine i_IOStatusError
    subroutine l_IOStatusError(stat, code)
        integer(8), intent(in) :: stat
        character(256) :: msg
        integer(bd), intent(out) :: code
        call retrieve_io_error_message(stat, msg)
        print *, 'IOStatusError: ', stat,  msg
        code = IOStatusErrorCode
    end subroutine l_IOStatusError

    subroutine n_ValueError(msg, code)
        character(*), intent(in) :: msg
        integer(bd), intent(out) :: code
        print *, 'ValueError: ' // msg
        code = ValueErrorCode
    end subroutine n_ValueError
    subroutine i_ValueError(msg, val, code)
        character(*), intent(in) :: msg
        integer, intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'ValueError: ' // msg
        print *, '    Recieved: ', val
        code = ValueErrorCode
    end subroutine i_ValueError
    subroutine l_ValueError(msg, val, code)
        character(*), intent(in) :: msg
        integer(8), intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'ValueError: ' // msg
        print *, '    Recieved: ', val
        code = ValueErrorCode
    end subroutine l_ValueError
    subroutine r_ValueError(msg, val, code)
        character(*), intent(in) :: msg
        real, intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'ValueError: ' // msg
        print *, '    Recieved: ', val
        code = ValueErrorCode
    end subroutine r_ValueError
    subroutine d_ValueError(msg, val, code)
        character(*), intent(in) :: msg
        double precision, intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'ValueError: ' // msg
        print *, '    Recieved: ', val
        code = ValueErrorCode
    end subroutine d_ValueError
    subroutine c_ValueError(msg, val, code)
        character(*), intent(in) :: msg
        character(*), intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'ValueError: ' // msg
        print *, '    Recieved: ', val
        code = ValueErrorCode
    end subroutine c_ValueError

    subroutine n_ValidRangeError(msg, code)
        character(*), intent(in) :: msg
        integer(bd), intent(out) :: code
        print *, 'ValidRangeError: ' // msg
        code = ValidRangeErrorCode
    end subroutine n_ValidRangeError
    subroutine i_ValidRangeError(msg, val, code)
        character(*), intent(in) :: msg
        integer, intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'ValidRangeError: ' // msg
        print *, '    Recieved: ', val
        code = ValidRangeErrorCode
    end subroutine i_ValidRangeError
    subroutine l_ValidRangeError(msg, val, code)
        character(*), intent(in) :: msg
        integer(8), intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'ValidRangeError: ' // msg
        print *, '    Recieved: ', val
        code = ValidRangeErrorCode
    end subroutine l_ValidRangeError
    subroutine r_ValidRangeError(msg, val, code)
        character(*), intent(in) :: msg
        real, intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'ValidRangeError: ' // msg
        print *, '    Recieved: ', val
        code = ValidRangeErrorCode
    end subroutine r_ValidRangeError
    subroutine d_ValidRangeError(msg, val, code)
        character(*), intent(in) :: msg
        double precision, intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'ValidRangeError: ' // msg
        print *, '    Recieved: ', val
        code = ValidRangeErrorCode
    end subroutine d_ValidRangeError
    subroutine i_mm_ValidRangeError(msg, vmin, vmax, val, code)
        character(*), intent(in) :: msg
        integer, intent(in) :: vmin, vmax, val
        integer(bd), intent(out) :: code
        print *, 'ValidRangeError: ' // msg
        print *, '    Recieved: ', val
        print *, '    Expected: vmin = ', vmin, 'vmax = ', vmax
        code = ValidRangeErrorCode
    end subroutine i_mm_ValidRangeError
    subroutine l_mm_ValidRangeError(msg, vmin, vmax, val, code)
        character(*), intent(in) :: msg
        integer(8), intent(in) :: vmin, vmax, val
        integer(bd), intent(out) :: code
        print *, 'ValidRangeError: ' // msg
        print *, '    Recieved: ', val
        print *, '    Expected: vmin = ', vmin, 'vmax = ', vmax
        code = ValidRangeErrorCode
    end subroutine l_mm_ValidRangeError
    subroutine r_mm_ValidRangeError(msg, vmin, vmax, val, code)
        character(*), intent(in) :: msg
        real, intent(in) :: vmin, vmax, val
        integer(bd), intent(out) :: code
        print *, 'ValidRangeError: ' // msg
        print *, '    Recieved: ', val
        print *, '    Expected: vmin = ', vmin, 'vmax = ', vmax
        code = ValidRangeErrorCode
    end subroutine r_mm_ValidRangeError
    subroutine d_mm_ValidRangeError(msg, vmin, vmax, val, code)
        character(*), intent(in) :: msg
        double precision, intent(in) :: vmin, vmax, val
        integer(bd), intent(out) :: code
        print *, 'ValidRangeError: ' // msg
        print *, '    Recieved: ', val
        print *, '    Expected: vmin = ', vmin, 'vmax = ', vmax
        code = ValidRangeErrorCode
    end subroutine d_mm_ValidRangeError

    subroutine n_Date_TimeError(msg, code)
        character(*), intent(in) :: msg
        integer(bd), intent(out) :: code
        print *, 'Date_TimeError: ' // msg
        code = Date_TimeErrorCode
    end subroutine n_Date_TimeError
    subroutine i_Date_TimeError(msg, val, code)
        character(*), intent(in) :: msg
        integer, intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'Date_TimeError: ' // msg
        print *, '    Recieved: ', val
        code = Date_TimeErrorCode
    end subroutine i_Date_TimeError
    subroutine l_Date_TimeError(msg, val, code)
        character(*), intent(in) :: msg
        integer(8), intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'Date_TimeError: ' // msg
        print *, '    Recieved: ', val
        code = Date_TimeErrorCode
    end subroutine l_Date_TimeError
    subroutine r_Date_TimeError(msg, val, code)
        character(*), intent(in) :: msg
        real, intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'Date_TimeError: ' // msg
        print *, '    Recieved: ', val
        code = Date_TimeErrorCode
    end subroutine r_Date_TimeError
    subroutine d_Date_TimeError(msg, val, code)
        character(*), intent(in) :: msg
        double precision, intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'Date_TimeError: ' // msg
        print *, '    Recieved: ', val
        code = Date_TimeErrorCode
    end subroutine d_Date_TimeError
    subroutine c_Date_TimeError(msg, val, code)
        character(*), intent(in) :: msg
        character(*), intent(in) :: val
        integer(bd), intent(out) :: code
        print *, 'Date_TimeError: ' // msg
        print *, '    Recieved: ', val
        code = Date_TimeErrorCode
    end subroutine c_Date_TimeError

    subroutine NotImplementedError(funcname, code)
        character(*), intent(in) :: funcname
        integer(bd), intent(out) :: code
        print *, 'NotImplementedError: ' // funcname
        code = NotImplementedErrorCode
    end subroutine NotImplementedError

end module errors
