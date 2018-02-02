module m_clip
    interface clip
        module procedure s_clip, i_clip, r_clip, d_clip
    end interface

    contains

    elemental function s_clip(val, vmin, vmax) result(ret)
        implicit none
        integer, parameter :: kk = 4
        integer(kk), intent(in) :: val, vmin, vmax
        integer(kk) :: ret
        include 'clip.h'
    end function
    elemental function i_clip(val, vmin, vmax) result(ret)
        implicit none
        integer, parameter :: kk = 8
        integer(kk), intent(in) :: val, vmin, vmax
        integer(kk) :: ret
        include 'clip.h'
    end function
    elemental function r_clip(val, vmin, vmax) result(ret)
        implicit none
        integer, parameter :: kk = 4
        real(kk), intent(in) :: val, vmin, vmax
        real(kk) :: ret
        include 'clip.h'
    end function
    elemental function d_clip(val, vmin, vmax) result(ret)
        implicit none
        integer, parameter :: kk = 8
        real(kk), intent(in) :: val, vmin, vmax
        real(kk) :: ret
        include 'clip.h'
    end function

    ! interface clip
    !     module procedure s_clip, i_clip, r_clip, d_clip
    ! end interface

    ! contains

    ! subroutine s_clip(val, vmin, vmax, ret)
    !     implicit none
    !     integer, parameter :: kk = 4
    !     integer(kind=kk), intent(in) :: val, vmin, vmax
    !     integer(kind=kk), intent(out) :: ret
    !     include 'clip.h'
    ! end subroutine s_clip
    ! subroutine i_clip(val, vmin, vmax, ret)
    !     implicit none
    !     integer, parameter :: kk = 8
    !     integer(kind=kk), intent(in) :: val, vmin, vmax
    !     integer(kind=kk), intent(out) :: ret
    !     include 'clip.h'
    ! end subroutine i_clip
    ! subroutine r_clip(val, vmin, vmax, ret)
    !     implicit none
    !     integer, parameter :: kk = 4
    !     real(kind=kk), intent(in) :: val, vmin, vmax
    !     real(kind=kk), intent(out) :: ret
    !     include 'clip.h'
    ! end subroutine r_clip
    ! subroutine d_clip(val, vmin, vmax, ret)
    !     implicit none
    !     integer, parameter :: kk = 8
    !     real(kind=kk), intent(in) :: val, vmin, vmax
    !     real(kind=kk), intent(out) :: ret
    !     include 'clip.h'
    ! end subroutine d_clip
    ! subroutine s_1d_clip(val, vmin, vmax, ret)
    !     implicit none
    !     integer, parameter :: kk = 4
    !     integer(kind=kk), intent(in) :: val, vmin, vmax
    !     integer(kind=kk), intent(out) :: ret
    !     include 'clip.h'
    ! end subroutine s_1d_clip
    ! subroutine i_1d_clip(val, vmin, vmax, ret)
    !     implicit none
    !     integer, parameter :: kk = 8
    !     integer(kind=kk), intent(in) :: val, vmin, vmax
    !     integer(kind=kk), intent(out) :: ret
    !     include 'clip.h'
    ! end subroutine i_1d_clip
    ! subroutine r_1d_clip(val, vmin, vmax, ret)
    !     implicit none
    !     integer, parameter :: kk = 4
    !     real(kind=kk), intent(in) :: val, vmin, vmax
    !     real(kind=kk), intent(out) :: ret
    !     include 'clip.h'
    ! end subroutine r_1d_clip
    ! subroutine d_1d_clip(val, vmin, vmax, ret)
    !     implicit none
    !     integer, parameter :: kk = 8
    !     real(kind=kk), intent(in) :: val, vmin, vmax
    !     real(kind=kk), intent(out) :: ret
    !     include 'clip.h'
    ! end subroutine d_1d_clip
end module m_clip
