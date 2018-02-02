module m_mrgrnk
    public :: mrgrnk
    private :: s_mrgrnk, i_mrgrnk, r_mrgrnk, d_mrgrnk

    interface mrgrnk
        ! __________________________________________________________
        !   MRGRNK = Merge-sort ranking of an array
        !   For performance reasons, the first 2 passes are taken
        !   out of the standard loop, and use dedicated coding.
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_mrgrnk, i_mrgrnk, r_mrgrnk, d_mrgrnk
    end interface

    contains

    subroutine s_mrgrnk(xdont, irngt)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xvala, xvalb
        include 'mrgrnk.h'
    end subroutine s_mrgrnk
    subroutine i_mrgrnk(xdont, irngt)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(in) :: xdont
        integer(kind=kk) :: xvala, xvalb
        include 'mrgrnk.h'
    end subroutine i_mrgrnk
    subroutine r_mrgrnk(xdont, irngt)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xvala, xvalb
        include 'mrgrnk.h'
    end subroutine r_mrgrnk
    subroutine d_mrgrnk(xdont, irngt)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(in) :: xdont
        real(kind=kk) :: xvala, xvalb
        include 'mrgrnk.h'
    end subroutine d_mrgrnk
end module m_mrgrnk
