module m_rapknr
    implicit none

    public :: rapknr
    private :: s_rapknr, i_rapknr, r_rapknr, d_rapknr

    interface rapknr
        !  Ranks partially XDONT by IRNGT, up to order NORD, in decreasing order.
        !  rapknr = (rnkpar backwards)
        ! __________________________________________________________
        !  This routine uses a pivoting strategy such as the one of
        !  finding the median based on the quicksort algorithm, but
        !  we skew the pivot choice to try to bring it to NORD as
        !  fast as possible. It uses 2 temporary arrays, where it
        !  stores the indices of the values larger than the pivot
        !  (IHIGT), and the indices of values smaller than the pivot
        !  that we might still need later on (ILOWT). It iterates
        !  until it can bring the number of values in IHIGT to
        !  exactly NORD, and then uses an insertion sort to rank
        !  this set, since it is supposedly small.
        !  Michel Olagnon - Feb. 2011
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_rapknr, i_rapknr, r_rapknr, d_rapknr
    end interface rapknr

    contains

    subroutine s_rapknr(xdont, irngt, nord)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xmin, xmax
        include 'rapknr.h'
    end subroutine s_rapknr
    subroutine i_rapknr(xdont, irngt, nord)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xmin, xmax
        include 'rapknr.h'
    end subroutine i_rapknr
    subroutine r_rapknr(xdont, irngt, nord)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xmin, xmax
        include 'rapknr.h'
    end subroutine r_rapknr
    subroutine d_rapknr(xdont, irngt, nord)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xmin, xmax
        include 'rapknr.h'
    end subroutine d_rapknr

end module m_rapknr
