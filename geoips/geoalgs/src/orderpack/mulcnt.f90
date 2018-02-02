module m_mulcnt
    implicit none

    public :: mulcnt
    private :: s_mulcnt, i_mulcnt, r_mulcnt, d_mulcnt

    interface mulcnt
        !   MULCNT = Give for each array value its multiplicity
        !            (number of times that it appears in the array)
        ! __________________________________________________________
        !  Michel Olagnon - Mar. 2000
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_mulcnt, i_mulcnt, r_mulcnt, d_mulcnt
    end interface mulcnt

    contains

    subroutine s_mulcnt(xdont, imult)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xdont
        include 'mulcnt.h'
    end subroutine s_mulcnt
    subroutine i_mulcnt(xdont, imult)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xdont
        include 'mulcnt.h'
    end subroutine i_mulcnt
    subroutine r_mulcnt(xdont, imult)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xdont
        include 'mulcnt.h'
    end subroutine r_mulcnt
    subroutine d_mulcnt(xdont, imult)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xdont
        include 'mulcnt.h'
    end subroutine d_mulcnt

end module m_mulcnt
