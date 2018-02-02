module m_indmed
    implicit none

    public :: indmed
    private :: s_indmed, i_indmed, r_indmed, d_indmed

    interface indmed
        module procedure s_indmed, i_indmed, r_indmed, d_indmed
    end interface

    interface med
        module procedure s_med, i_med, r_med, d_med
    end interface

    contains

    subroutine s_indmed(xdont, indm)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xdont
        include 'indmed.h'
        call s_med(xdont, idont, indm)
    end subroutine s_indmed
    subroutine i_indmed(xdont, indm)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xdont
        include 'indmed.h'
        call i_med(xdont, idont, indm)
    end subroutine i_indmed
    subroutine r_indmed(xdont, indm)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xdont
        include 'indmed.h'
        call r_med(xdont, idont, indm)
    end subroutine r_indmed
    subroutine d_indmed(xdont, indm)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xdont
        include 'indmed.h'
        call d_med(xdont, idont, indm)
    end subroutine d_indmed

    recursive subroutine s_med(xdatt, idatt, ires_med)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension (:), intent (in) :: xdatt
        integer(kind=kk), parameter :: xhuge = huge (xdatt)
        integer(kind=kk) :: xwrk, xwrk1, xmed7, xmax, xmin
        include 'indmed_med_first.h'
        call s_med(xdatt, imedt(1:idon1), imed7)
        include 'indmed_med_second.h'
    end subroutine s_med
    recursive subroutine i_med(xdatt, idatt, ires_med)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension (:), intent (in) :: xdatt
        integer(kind=kk), parameter :: xhuge = huge (xdatt)
        integer(kind=kk) :: xwrk, xwrk1, xmed7, xmax, xmin
        include 'indmed_med_first.h'
        call i_med(xdatt, imedt(1:idon1), imed7)
        include 'indmed_med_second.h'
    end subroutine i_med
    recursive subroutine r_med(xdatt, idatt, ires_med)
        integer, parameter :: kk = 4
        real(kind=kk), dimension (:), intent (in) :: xdatt
        real(kind=kk), parameter :: xhuge = huge (xdatt)
        real(kind=kk) :: xwrk, xwrk1, xmed7, xmax, xmin
        include 'indmed_med_first.h'
        call r_med(xdatt, imedt(1:idon1), imed7)
        include 'indmed_med_second.h'
    end subroutine r_med
    recursive subroutine d_med(xdatt, idatt, ires_med)
        integer, parameter :: kk = 8
        real(kind=kk), dimension (:), intent (in) :: xdatt
        real(kind=kk), parameter :: xhuge = huge (xdatt)
        real(kind=kk) :: xwrk, xwrk1, xmed7, xmax, xmin
        include 'indmed_med_first.h'
        call d_med(xdatt, imedt(1:idon1), imed7)
        include 'indmed_med_second.h'
    end subroutine d_med
end module m_indmed
