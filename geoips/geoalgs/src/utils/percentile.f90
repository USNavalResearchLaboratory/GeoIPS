module m_percentile

    use m_mrgrnk

    implicit none

    public :: percentile
    private :: i_percentile, i_percentile_2d

    interface percentile
        module procedure s_percentile, s_percentile_2d, &
                         i_percentile, i_percentile_2d, &
                         r_percentile, r_percentile_2d, &
                         d_percentile, d_percentile_2d
    end interface

    contains

    !i_percentile_2d - percentile for 2d-integer arrays
    !r_percentile_2d - percentile for 2d-real(4) arrays
    !d_percentile_2d - percentile for 2d-real(8) arrays
    !----------------------------------------
    ! Subroutine to return the values of a given set of percentiles in a 1d array.
    ! Call it with:
    !   item = a real(8) 2d array
    !   perc = a real(8) 1d array representing the percentiles for which to return a value.
    !   mask = a logical 2d array indicating which locations in item to ignore.
    !          .true. means "ignore the value", .false. means "consider the value"
    !          (OPTIONAL)
    !
    ! Accepts: Real array item, real array percs
    ! Returns: Real array containing values at each percentile
    !----------------------------------------
    subroutine s_percentile_2d(item, percs, vals, mask)
        integer, parameter :: kk = 4
        integer(kind=kk), intent(in) :: item(:,:)
        integer(kind=kk), intent(in) :: percs(:)
        integer(kind=kk) :: temp(size(item))
        integer(kind=kk), intent(out) :: vals(size(percs))
        include 'percentile_2d.h'
        call s_percentile(temp, percs, vals, tempmask)
    end subroutine s_percentile_2d
    subroutine i_percentile_2d(item, percs, vals, mask)
        integer, parameter :: kk = 8
        integer(kind=kk), intent(in) :: item(:,:)
        integer(kind=kk), intent(in) :: percs(:)
        integer(kind=kk) :: temp(size(item))
        integer(kind=kk), intent(out) :: vals(size(percs))
        include 'percentile_2d.h'
        call i_percentile(temp, percs, vals, tempmask)
    end subroutine i_percentile_2d
    subroutine r_percentile_2d(item, percs, vals, mask)
        integer, parameter :: kk = 4
        real(kind=kk), intent(in) :: item(:,:)
        real(kind=kk), intent(in) :: percs(:)
        real(kind=kk) :: temp(size(item))
        real(kind=kk), intent(out) :: vals(size(percs))
        include 'percentile_2d.h'
        call r_percentile(temp, percs, vals, tempmask)
    end subroutine r_percentile_2d
    subroutine d_percentile_2d(item, percs, vals, mask)
        integer, parameter :: kk = 8
        real(kind=kk), intent(in) :: item(:,:)
        real(kind=kk), intent(in) :: percs(:)
        real(kind=kk) :: temp(size(item))
        real(kind=kk), intent(out) :: vals(size(percs))
        include 'percentile_2d.h'
        call d_percentile(temp, percs, vals, tempmask)
    end subroutine d_percentile_2d

    !i_percentile - percentile for 1d-integer arrays
    !r_percentile - percentile for 1d-real(4) arrays
    !d_percentile - percentile for 1d-real(8) arrays
    !----------------------------------------
    ! Subroutine to return the values of a given set of percentiles in a 1d array.
    ! Call it with:
    !   item = a real(8) 1d array
    !   perc = a real(8) 1d array representing the percentiles for which to return a value.
    !   mask = a logical 1d array indicating which locations in item to ignore.
    !          .true. means "ignore the value", .false. means "consider the value"
    !          (OPTIONAL)
    !
    ! Accepts: Real 1d array item, real 1d array percs
    ! Returns: Real array containing values at each percentile
    !----------------------------------------

    subroutine s_percentile(item, percs, vals, mask)
        integer, parameter :: kk = 4
        integer(kind=kk), intent(in) :: item(:)
        integer(kind=kk), intent(in) :: percs(:)
        integer(kind=kk), allocatable :: tempitem(:)
        integer(kind=kk), allocatable :: ranks(:)
        integer(kind=kk) :: inds(size(percs))
        integer(kind=kk), intent(out) :: vals(size(percs))
        integer(kind=kk) :: aind, tind, ngood
        include 'percentile_1d.h'
    end subroutine s_percentile
    subroutine i_percentile(item, percs, vals, mask)
        integer, parameter :: kk = 8
        integer(kind=kk), intent(in) :: item(:)
        integer(kind=kk), intent(in) :: percs(:)
        integer(kind=kk), allocatable :: tempitem(:)
        integer(kind=kk), allocatable :: ranks(:)
        integer(kind=kk) :: inds(size(percs))
        integer(kind=kk), intent(out) :: vals(size(percs))
        integer(kind=kk) :: aind, tind, ngood
        include 'percentile_1d.h'
    end subroutine i_percentile
    subroutine r_percentile(item, percs, vals, mask)
        integer, parameter :: kk = 4
        real(kind=kk), intent(in) :: item(:)
        real(kind=kk), intent(in) :: percs(:)
        real(kind=kk), allocatable :: tempitem(:)
        integer(kind=kk), allocatable :: ranks(:)
        integer(kind=kk) :: inds(size(percs))
        real(kind=kk), intent(out) :: vals(size(percs))
        integer(kind=kk) :: aind, tind, ngood
        include 'percentile_1d.h'
    end subroutine r_percentile
    subroutine d_percentile(item, percs, vals, mask)
        integer, parameter :: kk = 8
        real(kind=kk), intent(in) :: item(:)
        real(kind=kk), intent(in) :: percs(:)
        real(kind=kk), allocatable :: tempitem(:)
        integer(kind=kk), allocatable :: ranks(:)
        integer(kind=kk) :: inds(size(percs))
        real(kind=kk), intent(out) :: vals(size(percs))
        integer(kind=kk) :: aind, tind, ngood
        include 'percentile_1d.h'
    end subroutine d_percentile
end module m_percentile
