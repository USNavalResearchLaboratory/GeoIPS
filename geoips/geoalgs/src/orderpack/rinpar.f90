module m_rinpar
    implicit none

    public :: rinpar
    private :: s_rinpar, i_rinpar, r_rinpar, d_rinpar

    interface rinpar
        !  Ranks partially XDONT by IRNGT, up to order NORD = size (IRNGT)
        ! __________________________________________________________
        !  This subroutine uses insertion sort, limiting insertion
        !  to the first NORD values. It does not use any work array
        !  and is faster when NORD is very small (2-5), but worst case
        !  behavior can happen fairly probably (initially inverse sorted)
        !  In many cases, the refined quicksort method is faster.
        !  Michel Olagnon - Feb. 2000
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_rinpar, i_rinpar, r_rinpar, d_rinpar
    end interface rinpar

    contains

    subroutine s_rinpar(xdont, irngt, nord)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xwrk, xwrk1
        include 'rinpar.h'
    end subroutine s_rinpar
    subroutine i_rinpar(xdont, irngt, nord)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xwrk, xwrk1
        include 'rinpar.h'
    end subroutine i_rinpar
    subroutine r_rinpar(xdont, irngt, nord)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xwrk, xwrk1
        include 'rinpar.h'
    end subroutine r_rinpar
    subroutine d_rinpar(xdont, irngt, nord)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xwrk, xwrk1
        include 'rinpar.h'
    end subroutine d_rinpar

end module m_rinpar
