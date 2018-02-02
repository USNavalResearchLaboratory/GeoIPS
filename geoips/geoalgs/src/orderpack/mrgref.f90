module m_mrgref
    implicit none

    public :: mrgref
    private :: s_mrgref, i_mrgref, r_mrgref, d_mrgref

    interface mrgref
        !   Ranks array XVALT into index array IRNGT, using merge-sort
        ! __________________________________________________________
        !   This version is not optimized for performance, and is thus
        !   not as difficult to read as some other ones.
        !   Michel Olagnon - April 2000
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_mrgref, i_mrgref, r_mrgref, d_mrgref
    end interface mrgref

    contains

    subroutine s_mrgref(xvalt, irngt)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xvalt
        include 'mrgref.h'
    end subroutine s_mrgref
    subroutine i_mrgref(xvalt, irngt)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xvalt
        include 'mrgref.h'
    end subroutine i_mrgref
    subroutine r_mrgref(xvalt, irngt)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xvalt
        include 'mrgref.h'
    end subroutine r_mrgref
    subroutine d_mrgref(xvalt, irngt)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xvalt
        include 'mrgref.h'
    end subroutine d_mrgref
end module m_mrgref
