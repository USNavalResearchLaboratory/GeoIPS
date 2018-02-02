MODULE m_ctrper
    use m_mrgrnk

    implicit none

    public :: ctrper
    private :: s_ctrper, i_ctrper, r_ctrper, d_ctrper

    interface ctrper
        !   Permute array XVALT randomly, but leaving elements close
        !   to their initial locations (nearbyness is controled by PCLS).
        ! _________________________________________________________________
        !   The routine takes the 1...size(XVALT) index array as real
        !   values, takes a combination of these values and of random
        !   values as a perturbation of the index array, and sorts the
        !   initial set according to the ranks of these perturbated indices.
        !   The relative proportion of initial order and random order
        !   is 1-PCLS / PCLS, thus when PCLS = 0, there is no change in
        !   the order whereas the new order is fully random when PCLS = 1.
        !   Michel Olagnon - May 2000.
        !   Modified by: Jeremy Solbrig - Feb 2017
        ! _________________________________________________________________
        ! __________________________________________________________
        module procedure s_ctrper, i_ctrper, r_ctrper, d_ctrper
    end interface

    contains

    subroutine s_ctrper(xdont, pcls)
        integer :: kk = 4
        integer(kind=kk) dimension(:), intent(inout) :: xdont
        include 'ctrper.h'
    end subroutine s_ctrper
    subroutine i_ctrper(xdont, pcls)
        integer :: kk = 8
        integer(kind=kk) dimension(:), intent(inout) :: xdont
        include 'ctrper.h'
    end subroutine i_ctrper
    subroutine r_ctrper(xdont, pcls)
        integer :: kk = 4
        real(kind=kk) dimension(:), intent(inout) :: xdont
        include 'ctrper.h'
    end subroutine r_ctrper
    subroutine d_ctrper(xdont, pcls)
        integer :: kk = 8
        real(kind=kk) dimension(:), intent(inout) :: xdont
        include 'ctrper.h'
    end subroutine d_ctrper
end module m_ctrper
