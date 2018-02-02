module m_median
    implicit none

    public :: median
    private :: s_median, i_median, r_median, d_median

    interface median
        module procedure s_median, i_median, r_median, d_median
    end interface median

    contains

    function s_median(xdont) result(median)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: median
        integer(kind=kk), dimension(size(xdont)) :: xlowt, xhigt
        integer(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xwrk2, xwrk3, xmin, xmax
        include 'median.h'
    end function s_median
    function i_median(xdont) result(median)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: median
        integer(kind=kk), dimension(size(xdont)) :: xlowt, xhigt
        integer(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xwrk2, xwrk3, xmin, xmax
        include 'median.h'
    end function i_median
    function r_median(xdont) result(median)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: median
        real(kind=kk), dimension(size(xdont)) :: xlowt, xhigt
        real(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xwrk2, xwrk3, xmin, xmax
        include 'median.h'
    end function r_median
    function d_median(xdont) result(median)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: median
        real(kind=kk), dimension(size(xdont)) :: xlowt, xhigt
        real(kind=kk) :: xpiv, xpiv0, xwrk, xwrk1, xwrk2, xwrk3, xmin, xmax
        include 'median.h'
    end function d_median
end module m_median
