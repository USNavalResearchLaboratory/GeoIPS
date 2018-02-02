module m_normalize

    use m_clip

    interface normalize
        module procedure r_normalize, d_normalize
    end interface

    contains

    elemental function r_normalize(val, vmin, vmax, doclip) result(ret)
        implicit none
        integer, parameter :: kk = 4
        include 'normalize.h'
    end function r_normalize
    elemental function d_normalize(val, vmin, vmax, doclip) result(ret)
        implicit none
        integer, parameter :: kk = 8
        include 'normalize.h'
    end function d_normalize
end module m_normalize
