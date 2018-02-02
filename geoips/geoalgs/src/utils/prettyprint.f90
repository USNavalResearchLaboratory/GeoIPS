module prettyprint

    interface print_min_mean_max
        module procedure s_1d_pmmm, i_1d_pmmm, r_1d_pmmm, d_1d_pmmm, s_2d_pmmm, i_2d_pmmm, r_2d_pmmm, d_2d_pmmm
    end interface

    contains

    subroutine s_1d_pmmm(str, arr, mask)
        integer, parameter :: kk = 4
        integer(kind=kk), intent(in) :: arr(:)
        include 'prettyprint_1d_pmmm.h'
    end subroutine s_1d_pmmm
    subroutine i_1d_pmmm(str, arr, mask)
        integer, parameter :: kk = 8
        integer(kind=kk), intent(in) :: arr(:)
        include 'prettyprint_1d_pmmm.h'
    end subroutine i_1d_pmmm
    subroutine r_1d_pmmm(str, arr, mask)
        integer, parameter :: kk = 4
        real(kind=kk), intent(in) :: arr(:)
        include 'prettyprint_1d_pmmm.h'
    end subroutine r_1d_pmmm
    subroutine d_1d_pmmm(str, arr, mask)
        integer, parameter :: kk = 8
        real(kind=kk), intent(in) :: arr(:)
        include 'prettyprint_1d_pmmm.h'
    end subroutine d_1d_pmmm
    subroutine s_2d_pmmm(str, arr, mask)
        integer, parameter :: kk = 4
        integer(kind=kk), intent(in) :: arr(:,:)
        include 'prettyprint_2d_pmmm.h'
    end subroutine s_2d_pmmm
    subroutine i_2d_pmmm(str, arr, mask)
        integer, parameter :: kk = 8
        integer(kind=kk), intent(in) :: arr(:,:)
        include 'prettyprint_2d_pmmm.h'
    end subroutine i_2d_pmmm
    subroutine r_2d_pmmm(str, arr, mask)
        integer, parameter :: kk = 4
        real(kind=kk), intent(in) :: arr(:,:)
        include 'prettyprint_2d_pmmm.h'
    end subroutine r_2d_pmmm
    subroutine d_2d_pmmm(str, arr, mask)
        integer, parameter :: kk = 8
        real(kind=kk), intent(in) :: arr(:,:)
        include 'prettyprint_2d_pmmm.h'
    end subroutine d_2d_pmmm
end module prettyprint
