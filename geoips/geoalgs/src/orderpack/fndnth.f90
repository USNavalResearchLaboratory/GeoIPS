module m_fndnth
    implicit none

    public :: fndnth
    private :: s_fndnth, i_fndnth, r_fndnth, d_fndnth

    interface fndnth
        !  return nordth value of xdont, i.e fractile of order nord/size(xdont).
        ! ______________________________________________________________________
        !  this subroutine uses insertion sort, limiting insertion
        !  to the first nord values. it is faster when nord is very small (2-5),
        !  and it requires only a workarray of size nord and type of xdont,
        !  but worst case behavior can happen fairly probably (initially inverse
        !  sorted). in many cases, the refined quicksort method is faster.
        !  michel olagnon - aug. 2000
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_fndnth, i_fndnth, r_fndnth, d_fndnth
    end interface

    contains

    function s_fndnth(xdont, nord) result(fndnth)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension (:), intent (in) :: xdont
        integer(kind=kk) :: fndnth
        integer(kind=kk), dimension (nord) :: xwrkt
        integer(kind=kk) :: xwrk, xwrk1
        include 'fndnth.h'
    end function s_fndnth
    function i_fndnth(xdont, nord) result(fndnth)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension (:), intent (in) :: xdont
        integer(kind=kk) :: fndnth
        integer(kind=kk), dimension (nord) :: xwrkt
        integer(kind=kk) :: xwrk, xwrk1
        include 'fndnth.h'
    end function i_fndnth
    function r_fndnth(xdont, nord) result(fndnth)
        integer, parameter :: kk = 4
        real(kind=kk), dimension (:), intent (in) :: xdont
        real(kind=kk) :: fndnth
        real(kind=kk), dimension (nord) :: xwrkt
        real(kind=kk) :: xwrk, xwrk1
        include 'fndnth.h'
    end function r_fndnth
    function d_fndnth(xdont, nord) result(fndnth)
        integer, parameter :: kk = 8
        real(kind=kk), dimension (:), intent (in) :: xdont
        real(kind=kk) :: fndnth
        real(kind=kk), dimension (nord) :: xwrkt
        real(kind=kk) :: xwrk, xwrk1
        include 'fndnth.h'
    end function d_fndnth
end module m_fndnth
