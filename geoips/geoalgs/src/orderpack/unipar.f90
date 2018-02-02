module m_unipar
    implicit none

    public :: unipar
    private :: s_unipar, i_unipar, r_unipar, d_unipar

    interface unipar
        !  Ranks partially XDONT by IRNGT, up to order NORD at most,
        !  removing duplicate entries
        ! __________________________________________________________
        !  This routine uses a pivoting strategy such as the one of
        !  finding the median based on the quicksort algorithm, but
        !  we skew the pivot choice to try to bring it to NORD as
        !  quickly as possible. It uses 2 temporary arrays, where it
        !  stores the indices of the values smaller than the pivot
        !  (ILOWT), and the indices of values larger than the pivot
        !  that we might still need later on (IHIGT). It iterates
        !  until it can bring the number of values in ILOWT to
        !  exactly NORD, and then uses an insertion sort to rank
        !  this set, since it is supposedly small. At all times, the
        !  NORD first values in ILOWT correspond to distinct values
        !  of the input array.
        !  Michel Olagnon - Feb. 2000
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_unipar, i_unipar, r_unipar, d_unipar
    end interface unipar

    contains

    subroutine s_unipar(xdont, irngt, nord)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xpiv, xwrk, xwrk1, xmin, xmax, xpiv0
        include 'unipar.h'
    end subroutine s_unipar
    subroutine i_unipar(xdont, irngt, nord)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xpiv, xwrk, xwrk1, xmin, xmax, xpiv0
        include 'unipar.h'
    end subroutine i_unipar
    subroutine r_unipar(xdont, irngt, nord)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xpiv, xwrk, xwrk1, xmin, xmax, xpiv0
        include 'unipar.h'
    end subroutine r_unipar
    subroutine d_unipar(xdont, irngt, nord)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xpiv, xwrk, xwrk1, xmin, xmax, xpiv0
        include 'unipar.h'
    end subroutine d_unipar
end module m_unipar
