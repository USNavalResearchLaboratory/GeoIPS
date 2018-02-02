module m_rnkpar
    implicit none

    public :: rnkpar
    private :: s_rnkpar, i_rnkpar, r_rnkpar, d_rnkpar

    interface rnkpar
        !  Ranks partially XDONT by IRNGT, up to order NORD
        ! __________________________________________________________
        !  This routine uses a pivoting strategy such as the one of
        !  finding the median based on the quicksort algorithm, but
        !  we skew the pivot choice to try to bring it to NORD as
        !  fast as possible. It uses 2 temporary arrays, where it
        !  stores the indices of the values smaller than the pivot
        !  (ILOWT), and the indices of values larger than the pivot
        !  that we might still need later on (IHIGT). It iterates
        !  until it can bring the number of values in ILOWT to
        !  exactly NORD, and then uses an insertion sort to rank
        !  this set, since it is supposedly small.
        !  Michel Olagnon - Feb. 2000
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_rnkpar, i_rnkpar, r_rnkpar, d_rnkpar
    end interface rnkpar

    contains

    subroutine s_rnkpar(xdont, irngt, nord)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xmin, xmax
        include 'rnkpar.h'
    end subroutine s_rnkpar
    subroutine i_rnkpar(xdont, irngt, nord)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xmin, xmax
        include 'rnkpar.h'
    end subroutine i_rnkpar
    subroutine r_rnkpar(xdont, irngt, nord)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xmin, xmax
        include 'rnkpar.h'
    end subroutine r_rnkpar
    subroutine d_rnkpar(xdont, irngt, nord)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xmin, xmax
        include 'rnkpar.h'
    end subroutine d_rnkpar
end module m_rnkpar
