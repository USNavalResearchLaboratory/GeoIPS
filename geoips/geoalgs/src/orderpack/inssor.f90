module m_inssor
    implicit none

    public :: inssor
    private :: s_inssor, i_inssor, r_inssor, d_inssor

    interface inssor
        module procedure s_inssor, i_inssor, r_inssor, d_inssor
    end interface inssor

    contains

    subroutine s_inssor(xdont)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(inout) :: xdont
        integer(kind=kk) :: xwrk, xmin
        include 'inssor.h'
    end subroutine s_inssor
    subroutine i_inssor(xdont)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(inout) :: xdont
        integer(kind=kk) :: xwrk, xmin
        include 'inssor.h'
    end subroutine i_inssor
    subroutine r_inssor(xdont)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(inout) :: xdont
        integer(kind=kk) :: xwrk, xmin
        include 'inssor.h'
    end subroutine r_inssor
    subroutine d_inssor(xdont)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(inout) :: xdont
        real(kind=kk) :: xwrk, xmin
        include 'inssor.h'
    end subroutine d_inssor
end module m_inssor
