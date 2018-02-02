module m_indnth
    implicit none
    public :: indnth
    private :: s_indnth, i_indnth, r_indnth, d_indnth

    interface indnth
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
        module procedure s_indnth, i_indnth, r_indnth, d_indnth
    end interface indnth

    contains

    function s_indnth(xdont, nord) result(indnth)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xmin, xmax
        include 'indnth.h'
    end function s_indnth 
    function i_indnth(xdont, nord) result(indnth)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xmin, xmax
        include 'indnth.h'
    end function i_indnth
    function r_indnth(xdont, nord) result(indnth)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xmin, xmax
        include 'indnth.h'
    end function r_indnth
    function d_indnth(xdont, nord) result(indnth)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xmin, xmax
        include 'indnth.h'
    end function d_indnth
end module m_indnth
