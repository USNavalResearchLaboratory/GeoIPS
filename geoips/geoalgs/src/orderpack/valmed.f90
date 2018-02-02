module m_valmed
    implicit none

    public :: valmed
    private :: s_valmed, i_valmed, r_valmed, d_valmed

    interface valmed
        !  Finds the median of XDONT using the recursive procedure
        !  described in Knuth, The Art of Computer Programming,
        !  vol. 3, 5.3.3 - This procedure is linear in time, and
        !  does not require to be able to interpolate in the
        !  set as the one used in INDNTH. It also has better worst
        !  case behavior than INDNTH, but is about 30% slower in
        !  average for random uniformly distributed values.
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_valmed, i_valmed, r_valmed, d_valmed
    end interface valmed

    contains

    recursive function s_valmed(xdont) result(res_med)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: res_med
        integer(kind=kk), parameter :: xhuge = huge(xdont)
        integer(kind=kk), dimension(size(xdont)+6) :: xwrkt
        integer(kind=kk) :: xwrk, xwrk1, xmed7
        include 'valmed_valmed_first.h'
        xmed7 = s_valmed(xwrkt (imedt))
        include 'valmed_valmed_second.h'
    end function s_valmed
    recursive function i_valmed(xdont) result(res_med)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: res_med
        integer(kind=kk), parameter :: xhuge = huge(xdont)
        integer(kind=kk), dimension(size(xdont)+6) :: xwrkt
        integer(kind=kk) :: xwrk, xwrk1, xmed7
        include 'valmed_valmed_first.h'
        xmed7 = i_valmed(xwrkt (imedt))
        include 'valmed_valmed_second.h'
    end function i_valmed
    recursive function r_valmed(xdont) result(res_med)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: res_med
        real(kind=kk), parameter :: xhuge = huge(xdont)
        real(kind=kk), dimension(size(xdont)+6) :: xwrkt
        real(kind=kk) :: xwrk, xwrk1, xmed7
        include 'valmed_valmed_first.h'
        xmed7 = r_valmed(xwrkt (imedt))
        include 'valmed_valmed_second.h'
    end function r_valmed
    recursive function d_valmed(xdont) result(res_med)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: res_med
        real(kind=kk), parameter :: xhuge = huge(xdont)
        real(kind=kk), dimension(size(xdont)+6) :: xwrkt
        real(kind=kk) :: xwrk, xwrk1, xmed7
        include 'valmed_valmed_first.h'
        xmed7 = d_valmed(xwrkt (imedt))
        include 'valmed_valmed_second.h'
    end function d_valmed
end module m_valmed

