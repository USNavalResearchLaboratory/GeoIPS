program test_io_messages
    use io_messages
    implicit none
    character(256) :: msg
    call retrieve_io_error_message(199, msg)
    print *, msg
end program test_io_messages
