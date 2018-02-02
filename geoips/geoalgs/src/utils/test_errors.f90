program test_errors
    use errors

    implicit none

    integer :: code

    call ValueError('testing None', code)
    call ValueError('testing Integer', 42, code)
    call ValueError('testing Float', 42.0, code)
    call ValueError('testing Double', 4.2d2, code)
    call ValueError('testing Char', 'FourtyTwo', code)

end program test_errors
