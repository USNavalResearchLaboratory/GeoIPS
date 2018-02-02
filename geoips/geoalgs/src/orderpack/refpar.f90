module m_refpar
    implicit none

    public :: refpar
    private :: s_refpar, i_refpar, r_refpar, d_refpar

    interface refpar
        !  Ranks partially XDONT by IRNGT, up to order NORD
        ! __________________________________________________________
        !  This routine uses a pivoting strategy such as the one of
        !  finding the median based on the quicksort algorithm. It uses
        !  a temporary array, where it stores the partially ranked indices
        !  of the values. It iterates until it can bring the number of
        !  values lower than the pivot to exactly NORD, and then uses an
        !  insertion sort to rank this set, since it is supposedly small.
        !  Michel Olagnon - Feb. 2000
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_refpar, i_refpar, r_refpar, d_refpar
    end interface refpar

    contains

    subroutine s_refpar(xdont, irngt, nord)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xpiv, xwrk
        include 'refpar.h'
    end subroutine s_refpar
    subroutine i_refpar(xdont, irngt, nord)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xpiv, xwrk
        include 'refpar.h'
    end subroutine i_refpar
    subroutine r_refpar(xdont, irngt, nord)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xpiv, xwrk
        include 'refpar.h'
    end subroutine r_refpar
    subroutine d_refpar(xdont, irngt, nord)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xpiv, xwrk
        include 'refpar.h'
    end subroutine d_refpar
end module m_refpar
