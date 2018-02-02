module m_unirnk
    implicit none

    public :: unirnk
    private :: s_unirnk, i_unirnk, r_unirnk, d_unirnk
    private :: s_nearless, i_nearless, r_nearless, d_nearless, nearless

    interface unirnk
        ! __________________________________________________________
        !   UNIRNK = Merge-sort ranking of an array, with removal of
        !   duplicate entries.
        !   The routine is similar to pure merge-sort ranking, but on
        !   the last pass, it discards indices that correspond to
        !   duplicate entries.
        !   For performance reasons, the first 2 passes are taken
        !   out of the standard loop, and use dedicated coding.
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_unirnk, i_unirnk, r_unirnk, d_unirnk
    end interface unirnk

    interface nearless
        !  Nearest value less than given value
        ! __________________________________________________________
        module procedure s_nearless, i_nearless, r_nearless, d_nearless
    end interface nearless

    contains

    subroutine s_unirnk(xvalt, irngt, nuni)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xvalt
        integer(kind=kk) :: xtst, xvala, xvalb
        include 'unirnk.h'
    end subroutine s_unirnk
    subroutine i_unirnk(xvalt, irngt, nuni)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xvalt
        integer(kind=kk) :: xtst, xvala, xvalb
        include 'unirnk.h'
    end subroutine i_unirnk
    subroutine r_unirnk(xvalt, irngt, nuni)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xvalt
        real(kind=kk) :: xtst, xvala, xvalb
        include 'unirnk.h'
    end subroutine r_unirnk
    subroutine d_unirnk(xvalt, irngt, nuni)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xvalt
        real(kind=kk) :: xtst, xvala, xvalb
        include 'unirnk.h'
    end subroutine d_unirnk

    function s_nearless(xval) result(s_nl)
        integer, parameter :: kk = 4
        integer(kind=kk), intent(in) :: xval
        integer(kind=kk) :: s_nl
        s_nl = xval - 1
        return
    end function s_nearless
    function i_nearless(xval) result(i_nl)
        integer, parameter :: kk = 8
        integer(kind=kk), intent(in) :: xval
        integer(kind=kk) :: i_nl
        i_nl = xval - 1
        return
    end function i_nearless
    function r_nearless(xval) result(r_nl)
        integer, parameter :: kk = 4
        real(kind=kk), intent(in) :: xval
        real(kind=kk) :: r_nl
        r_nl = nearest(xval, -1.0)
        return
    end function r_nearless
    function d_nearless(xval) result(d_nl)
        integer, parameter :: kk = 8
        real(kind=kk), intent(in) :: xval
        real(kind=kk) :: d_nl
        d_nl = nearest(xval, -1.0)
        return
    end function d_nearless
end module m_unirnk
