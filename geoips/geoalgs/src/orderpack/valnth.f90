module m_valmed
    implicit none

    public :: valnth
    private :: s_valnth, i_valnth, r_valnth, d_valnth

    interface valnth
        !  Return NORDth value of XDONT, i.e fractile of order NORD/SIZE(XDONT).
        ! __________________________________________________________
        !  This routine uses a pivoting strategy such as the one of
        !  finding the median based on the quicksort algorithm, but
        !  we skew the pivot choice to try to bring it to NORD as
        !  fast as possible. It uses 2 temporary arrays, where it
        !  stores the indices of the values smaller than the pivot
        !  (ILOWT), and the indices of values larger than the pivot
        !  that we might still need later on (IHIGT). It iterates
        !  until it can bring the number of values in ILOWT to
        !  exactly NORD, and then finds the maximum of this set.
        !  Michel Olagnon - Aug. 2000
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_valnth, i_valnth, r_valnth, d_valnth
    end interface valnth

    contains

    function s_valnth(xdont, nord) result(valnth)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: valnth
        integer(kind=kk), dimension(size(xdont)) :: xlowt, xhigt
        integer(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xwrk2, xwrk3, xmin, xmax
        include 'valnth.h'
    end function s_valnth
    function i_valnth(xdont, nord) result(valnth)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: valnth
        integer(kind=kk), dimension(size(xdont)) :: xlowt, xhigt
        integer(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xwrk2, xwrk3, xmin, xmax
        include 'valnth.h'
    end function i_valnth
    function r_valnth(xdont, nord) result(valnth)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: valnth
        real(kind=kk), dimension(size(xdont)) :: xlowt, xhigt
        real(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xwrk2, xwrk3, xmin, xmax
        include 'valnth.h'
    end function r_valnth
    function d_valnth(xdont, nord) result(valnth)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: valnth
        real(kind=kk), dimension(size(xdont)) :: xlowt, xhigt
        real(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xwrk2, xwrk3, xmin, xmax
        include 'valnth.h'
    end function d_valnth
end module m_valmed
