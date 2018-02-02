module m_inspar
    implicit none

    public :: inspar
    private :: s_inspar, i_inspar, r_inspar, d_inspar

    interface inspar
        module procedure s_inspar, i_inspar, r_inspar, d_inspar
    end interface inspar

    contains

    subroutine s_inspar(xdont, nord)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(inout) :: xdont
        integer(kind=kk) :: xwrk, xwrk1
        include 'inspar.h'
    end subroutine s_inspar
    subroutine i_inspar(xdont, nord)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(inout) :: xdont
        integer(kind=kk) :: xwrk, xwrk1
        include 'inspar.h'
    end subroutine i_inspar
    subroutine r_inspar(xdont, nord)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(inout) :: xdont
        real(kind=kk) :: xwrk, xwrk1
        include 'inspar.h'
    end subroutine r_inspar
    subroutine d_inspar(xdont, nord)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(inout) :: xdont
        real(kind=kk) :: xwrk, xwrk1
        include 'inspar.h'
    end subroutine d_inspar
end module m_inspar
