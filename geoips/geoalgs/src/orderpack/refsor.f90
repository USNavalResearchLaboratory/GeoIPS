module m_refsor
    implicit none

    public :: refsor
    private :: s_refsor, i_refsor, r_refsor, d_refsor

    interface refsor
        !  Sorts XDONT into ascending order - Quicksort
        ! __________________________________________________________
        !  Quicksort chooses a "pivot" in the set, and explores the
        !  array from both ends, looking for a value > pivot with the
        !  increasing index, for a value <= pivot with the decreasing
        !  index, and swapping them when it has found one of each.
        !  The array is then subdivided in 2 ([3]) subsets:
        !  { values <= pivot} {pivot} {values > pivot}
        !  One then call recursively the program to sort each subset.
        !  When the size of the subarray is small enough, one uses an
        !  insertion sort that is faster for very small sets.
        !  Michel Olagnon - Apr. 2000
        ! __________________________________________________________
        ! __________________________________________________________
        module procedure s_refsor, i_refsor, r_refsor, d_refsor
    end interface refsor

    contains

    subroutine s_refsor(xdont)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(inout) :: xdont
        call s_subsor(xdont, 1, size(xdont))
        call s_inssor(xdont)
    end subroutine s_refsor
    subroutine i_refsor(xdont)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(inout) :: xdont
        call i_subsor(xdont, 1, size(xdont))
        call i_inssor(xdont)
    end subroutine i_refsor
    subroutine r_refsor(xdont)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(inout) :: xdont
        call r_subsor(xdont, 1, size(xdont))
        call r_inssor(xdont)
    end subroutine r_refsor
    subroutine d_refsor(xdont)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(inout) :: xdont
        call d_subsor(xdont, 1, size(xdont))
        call d_inssor(xdont)
    end subroutine d_refsor

    recursive subroutine s_subsor(xdont, ideb1, ifin1)
        integer, parameter :: kk = 4
        integer(kind=kk), dimension(:), intent(inout) :: xdont
        integer(kind=kk) :: xpiv, xwrk
        include 'refsor_subsor_first.h'
        call s_subsor(xdont, ideb1, icrs-1)
        call s_subsor(xdont, idcr, ifin1)
        include 'refsor_subsor_second.h'
    end subroutine s_subsor
    recursive subroutine i_subsor(xdont, ideb1, ifin1)
        integer, parameter :: kk = 8
        integer(kind=kk), dimension(:), intent(inout) :: xdont
        integer(kind=kk) :: xpiv, xwrk
        include 'refsor_subsor_first.h'
        call i_subsor(xdont, ideb1, icrs-1)
        call i_subsor(xdont, idcr, ifin1)
        include 'refsor_subsor_second.h'
    end subroutine i_subsor
    recursive subroutine r_subsor(xdont, ideb1, ifin1)
        integer, parameter :: kk = 4
        real(kind=kk), dimension(:), intent(inout) :: xdont
        real(kind=kk) :: xpiv, xwrk
        include 'refsor_subsor_first.h'
        call r_subsor(xdont, ideb1, icrs-1)
        call r_subsor(xdont, idcr, ifin1)
        include 'refsor_subsor_second.h'
    end subroutine r_subsor
    recursive subroutine d_subsor(xdont, ideb1, ifin1)
        integer, parameter :: kk = 8
        real(kind=kk), dimension(:), intent(inout) :: xdont
        real(kind=kk) :: xpiv, xwrk
        include 'refsor_subsor_first.h'
        call d_subsor(xdont, ideb1, icrs-1)
        call d_subsor(xdont, idcr, ifin1)
        include 'refsor_subsor_second.h'
    end subroutine d_subsor

end module m_refsor
