module m_uniinv
    implicit none

    public :: uniinv
    private :: s_uniinv, i_uniinv, r_uniinv, d_uniinv
    private :: s_nearless, i_nearless, r_nearless, d_nearless, nearless

    interface uniinv
        ! __________________________________________________________
        !   UNIINV = Merge-sort inverse ranking of an array, with removal of
        !   duplicate entries.
        !   The routine is similar to pure merge-sort ranking, but on
        !   the last pass, it sets indices in IGOEST to the rank
        !   of the value in the ordered set with duplicates removed.
        !   For performance reasons, the first 2 passes are taken
        !   out of the standard loop, and use dedicated coding.
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_uniinv, i_uniinv, r_uniinv, d_uniinv
    end interface uniinv

    interface nearless
        !  Nearest value less than given value
        ! __________________________________________________________
        module procedure s_nearless, i_nearless, r_nearless, d_nearless
    end interface nearless

    contains

    subroutine s_uniinv(xdont, igoest)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xtst, xdona, xdonb
        include 'uniinv.h'
    end subroutine s_uniinv
    subroutine i_uniinv(xdont, igoest)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xtst, xdona, xdonb
        include 'uniinv.h'
    end subroutine i_uniinv
    subroutine r_uniinv(xdont, igoest)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xtst, xdona, xdonb
        include 'uniinv.h'
    end subroutine r_uniinv
    subroutine d_uniinv(xdont, igoest)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xtst, xdona, xdonb
        include 'uniinv.h'
    end subroutine d_uniinv

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
end module m_uniinv
