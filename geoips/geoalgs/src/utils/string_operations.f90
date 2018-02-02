MODULE string_operations

    CONTAINS

    FUNCTION to_upper(strIn) RESULT(strOut)
        ! Converts the input string to all upper case
        ! Adapted from http://www.star.le.ac.ky/~cgp/fortran.html
        IMPLICIT NONE

        CHARACTER(LEN=*), INTENT(IN) :: strIn
        CHARACTER(LEN=LEN(strIn)) :: strOut
        INTEGER :: char_ind, ascii_val

        DO char_ind = 1, LEN(strIn)
            ascii_val = iachar(strIn(char_ind:char_ind))
            IF (ascii_val >= iachar("a") .AND. ascii_val <= iachar("z")) THEN
                strOut(char_ind:char_ind) = achar(iachar(strIn(char_ind:char_ind)) - 32)
            ELSE
                strOut(char_ind:char_ind) = strIn(char_ind:char_ind)
            END IF
        END DO
    END FUNCTION to_upper

    FUNCTION to_lower(strIn) RESULT(strOut)
        ! Converts the input string to all lower case
        ! Adapted from http://www.star.le.ac.ky/~cgp/fortran.html
        IMPLICIT NONE

        CHARACTER(LEN=*), INTENT(IN) :: strIn
        CHARACTER(LEN=LEN(strIn)) :: strOut
        INTEGER :: char_ind, ascii_val

        DO char_ind = 1, LEN(strIn)
            ascii_val = iachar(strIn(char_ind:char_ind))
            IF (ascii_val >= iachar("A") .AND. ascii_val <= iachar("Z")) THEN
                strOut(char_ind:char_ind) = achar(iachar(strIn(char_ind:char_ind)) + 32)
            ELSE
                strOut(char_ind:char_ind) = strIn(char_ind:char_ind)
            END IF
        END DO
    END FUNCTION to_lower

END MODULE string_operations
