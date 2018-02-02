module error_codes
    use io_messages
    implicit none

    integer, parameter, private :: bd = 8

    integer(bd) :: ValueErrorCode = 330
    integer(bd) :: ValidRangeErrorCode = 331
    integer(bd) :: NoSuchFileCode = 340
    integer(bd) :: Date_TimeErrorCode = 350
    integer(bd) :: IOStatusErrorCode = 360
    integer(bd) :: NotImplementedErrorCode = 370

    !f2py integer(bd) :: ValueErrorCode, ValidRangeErrorCode, NoSuchFileCode, Date_TimeErrorCode,
    !f2py integer(bd) :: IOStatusErrorCode, NotImplementedErrorCode
end module error_codes
