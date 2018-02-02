module m_unista
    implicit none

    public :: unista
    private :: s_unista, i_unista, r_unista, d_unista

    interface unista
        module procedure s_unista, i_unista, r_unista, d_unista
    end interface unista

    contains

    subroutine s_unista(xdont, nuni)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(inout) :: xdont
        include 'unista.h'
    end subroutine s_unista
    subroutine i_unista(xdont, nuni)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(inout) :: xdont
        include 'unista.h'
    end subroutine i_unista
    subroutine r_unista(xdont, nuni)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(inout) :: xdont
        include 'unista.h'
    end subroutine r_unista
    subroutine d_unista(xdont, nuni)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(inout) :: xdont
        include 'unista.h'
    end subroutine d_unista
end module m_unista
