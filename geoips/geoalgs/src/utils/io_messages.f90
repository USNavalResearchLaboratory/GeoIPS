module io_messages

    use config

    implicit none
    integer, parameter, private :: bd = 8

    interface retrieve_io_error_message
        module procedure i_retrieve_io_error_message, l_retrieve_io_error_message
    endinterface

    integer(bd), dimension(-4:199) :: locs = &
        (/ 1, -1, 2, 3, -1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, &
        19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, &
        -1, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, -1, -1, -1, 52, &
        -1, -1, 53, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, &
        -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55, 56, 57, 58, 59, -1, 60, -1, &
        61, 62, 63, 64, 65, 66, 67, -1, -1, -1, -1, -1, -1, -1, -1, 68, -1, -1, 69, &
        -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, 71, 72, -1, -1, 73, -1, 74, 75, 76, &
        77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, -1, 90, 91, -1, -1, -1, &
        -1, -1, 92, 93, 94, -1, -1, 95, -1, -1, 96, -1, -1, -1, 97, 98, 99, -1, -1, &
        -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 100, 101, -1, &
        102, 103, -1, -1, -1, 104, 105, 106, 107, 108, 109, 110, 111, 112 /)

    integer(bd), dimension(112) :: codes = (/ &
        -4, -2, -1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, &
        17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, &
        34, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 53, 56, &
        58, 84, 85, 86, 87, 88, 90, 92, 93, 94, 95, 96, 97, 98, 107, &
        110, 120, 121, 122, 125, 127, 128, 129, 130, 131, 132, 133, 134, &
        135, 136, 137, 138, 139, 140, 141, 142, 144, 145, 151, 152, 153, &
        156, 159, 163, 164, 165, 183, 184, 186, 187, 191, 192, 193, 194, &
        195, 196, 197, 198, 199 /)
    character(len=256), parameter :: message_m004 = "End of record encountered on a nonadvancing, " // &
        "format-directed READ of an external file."
    character(len=256), parameter :: message_m002 = "End of file encountered on READ of an internal file."
    character(len=256), parameter :: message_m001 = "End of file encountered on sequential or stream READ " // &
        "of an external file, or END= is specified on a direct access read and the record is nonexistent."
    character(len=256), parameter :: message_001 = "END= is not specified on a direct access READ and the record is nonexistent."
    character(len=256), parameter :: message_002 = "End of file encountered on WRITE of an internal file."
    character(len=256), parameter :: message_003 = "End of record encountered on an unformatted file."
    character(len=256), parameter :: message_004 = "End of record encountered on a formatted external file using advancing I/O."
    character(len=256), parameter :: message_005 = "End of record encountered on an internal file."
    character(len=256), parameter :: message_006 = "File cannot be found and STATUS='OLD' is specified on an OPEN statement."
    character(len=256), parameter :: message_007 = "Incorrect format of list-directed input found in an external file."
    character(len=256), parameter :: message_008 = "Incorrect format of list-directed input found in an internal file."
    character(len=256), parameter :: message_009 = "List-directed or NAMELIST data item too long for the internal file."
    character(len=256), parameter :: message_010 = "Read error on direct file."
    character(len=256), parameter :: message_011 = "Write error on direct file."
    character(len=256), parameter :: message_012 = "Read error on sequential or stream file."
    character(len=256), parameter :: message_013 = "Write error on sequential or stream file."
    character(len=256), parameter :: message_014 = "Error opening file."
    character(len=256), parameter :: message_015 = "Permanent I/O error encountered on file."
    character(len=256), parameter :: message_016 = "Value of REC= specifier invalid on direct I/O."
    character(len=256), parameter :: message_017 = "I/O statement not allowed on direct file."
    character(len=256), parameter :: message_018 = "Direct I/O statement on an unconnected unit."
    character(len=256), parameter :: message_019 = "Unformatted I/O attempted on formatted file."
    character(len=256), parameter :: message_020 = "Formatted I/O attempted on unformatted file."
    character(len=256), parameter :: message_021 = "Sequential or stream I/O attempted on direct file."
    character(len=256), parameter :: message_022 = "Direct I/O attempted on sequential or stream file."
    character(len=256), parameter :: message_023 = "Attempt to connect a file that is already connected to another unit."
    character(len=256), parameter :: message_024 = "OPEN specifiers do not match the connected file's attributes."
    character(len=256), parameter :: message_025 = "RECL= specifier omitted on an OPEN statement for a direct file."
    character(len=256), parameter :: message_026 = "RECL= specifier on an OPEN statement is negative."
    character(len=256), parameter :: message_027 = "ACCESS= specifier on an OPEN statement is invalid."
    character(len=256), parameter :: message_028 = "FORM= specifier on an OPEN statement is invalid."
    character(len=256), parameter :: message_029 = "STATUS= specifier on an OPEN statement is invalid."
    character(len=256), parameter :: message_030 = "BLANK= specifier on an OPEN statement is invalid."
    character(len=256), parameter :: message_031 = "FILE= specifier on an OPEN or INQUIRE statement is invalid."
    character(len=256), parameter :: message_032 = "STATUS='SCRATCH' and FILE= specifier specified on same OPEN statement."
    character(len=256), parameter :: message_033 = "STATUS='KEEP' specified on CLOSE statement when file was " // &
        "opened with STATUS='SCRATCH'."
    character(len=256), parameter :: message_034 = "Value of STATUS= specifier on CLOSE statement is invalid."
    character(len=256), parameter :: message_036 = "Invalid unit number specified in an I/O statement."
    character(len=256), parameter :: message_037 = "Dynamic memory allocation failure - out of memory."
    character(len=256), parameter :: message_038 = "REWIND error."
    character(len=256), parameter :: message_039 = "ENDFILE error."
    character(len=256), parameter :: message_040 = "BACKSPACE error."
    character(len=256), parameter :: message_041 = "Valid logical input not found in external file."
    character(len=256), parameter :: message_042 = "Valid logical input not found in internal file."
    character(len=256), parameter :: message_043 = "Complex value expected using list-directed or NAMELIST " // &
        "input in external file but not found."
    character(len=256), parameter :: message_044 = "Complex value expected using list-directed or NAMELIST " // &
        "input in internal file but not found."
    character(len=256), parameter :: message_045 = "NAMELIST item name specified with unknown or invalid " // &
        "derived-type component name in NAMELIST input."
    character(len=256), parameter :: message_046 = "NAMELIST item name specified with an invalid substring range in NAMELIST input."
    character(len=256), parameter :: message_047 = "A namelist input item was specified with one or more " // &
        "components of nonzero rank."
    character(len=256), parameter :: message_048 = "A namelist input item specified a zero-sized array."
    character(len=256), parameter :: message_049 = "List-directed or namelist input contained an invalid " // &
        "delimited character string."
    character(len=256), parameter :: message_053 = "Mismatched edit descriptor and item type in formatted I/O."
    character(len=256), parameter :: message_056 = "Invalid digit found in input for B, O or Z format edit descriptors."
    character(len=256), parameter :: message_058 = "Format specification error."
    character(len=256), parameter :: message_084 = "NAMELIST group header not found in external file."
    character(len=256), parameter :: message_085 = "NAMELIST group header not found in internal file."
    character(len=256), parameter :: message_086 = "Invalid NAMELIST input value found in external file."
    character(len=256), parameter :: message_087 = "Invalid NAMELIST input value found in internal file."
    character(len=256), parameter :: message_088 = "Invalid name found in NAMELIST input."
    character(len=256), parameter :: message_090 = "Invalid character in NAMELIST group or item name in input."
    character(len=256), parameter :: message_092 = "Invalid subscript list for NAMELIST item in input."
    character(len=256), parameter :: message_093 = "I/O statement not allowed on error unit (unit 0)."
    character(len=256), parameter :: message_094 = "Invalid repeat specifier for list-directed or NAMELIST input in external file."
    character(len=256), parameter :: message_095 = "Invalid repeat specifier for list-directed or NAMELIST input in internal file."
    character(len=256), parameter :: message_096 = "Integer overflow in input."
    character(len=256), parameter :: message_097 = "Invalid decimal digit found in input."
    character(len=256), parameter :: message_098 = "Input too long for B, O or Z format edit descriptors."
    character(len=256), parameter :: message_107 = "File exists and STATUS='NEW' was specified on an OPEN statement."
    character(len=256), parameter :: message_110 = "Illegal edit descriptor used with a data item in formatted I/O."
    character(len=256), parameter :: message_120 = "The NLWIDTH setting exceeds the length of a record."
    character(len=256), parameter :: message_121 = "Output length of NAMELIST item name or NAMELIST group " // &
        "name is longer than the maximum record length or the output width specified by the NLWIDTH option."
    character(len=256), parameter :: message_122 = "Incomplete record encountered during direct access READ."
    character(len=256), parameter :: message_125 = "BLANK= specifier given on an OPEN statement for an unformatted file."
    character(len=256), parameter :: message_127 = "POSITION= specifier given on an OPEN statement for a direct file."
    character(len=256), parameter :: message_128 = "POSITION= specifier value on an OPEN statement is invalid."
    character(len=256), parameter :: message_129 = "ACTION= specifier value on an OPEN statement is invalid."
    character(len=256), parameter :: message_130 = "ACTION='READWRITE' specified on an OPEN statement to connect a pipe."
    character(len=256), parameter :: message_131 = "DELIM= specifier given on an OPEN statement for an unformatted file."
    character(len=256), parameter :: message_132 = "DELIM= specifier value on an OPEN statement is invalid."
    character(len=256), parameter :: message_133 = "PAD= specifier given on an OPEN statement for an unformatted file."
    character(len=256), parameter :: message_134 = "PAD= specifier value on an OPEN statement is invalid."
    character(len=256), parameter :: message_135 = "The user program is making calls to an unsupported version " // &
        "of the XL Fortran run-time environment."
    character(len=256), parameter :: message_136 = "ADVANCE= specifier value on a READ statement is invalid."
    character(len=256), parameter :: message_137 = "ADVANCE='NO' is not specified when SIZE= is specified on a READ statement."
    character(len=256), parameter :: message_138 = "ADVANCE='NO' is not specified when EOR= is specified on a READ statement."
    character(len=256), parameter :: message_139 = "I/O operation not permitted on the unit because the file was not " // &
        "opened with an appropriate value for the ACTION= specifier."
    character(len=256), parameter :: message_140 = "Unit is not connected when the I/O statement is attempted. " // &
        "Only for READ, WRITE, PRINT, REWIND, and ENDFILE."
    character(len=256), parameter :: message_141 = "Two ENDFILE statements without an intervening REWIND or BACKSPACE on the unit."
    character(len=256), parameter :: message_142 = "CLOSE error."
    character(len=256), parameter :: message_144 = "INQUIRE error."
    character(len=256), parameter :: message_145 = "READ or WRITE attempted when file is positioned after the endfile record."
    character(len=256), parameter :: message_151 = "The FILE= specifier is missing and the STATUS= specifier " // &
        "does not have a value of 'SCRATCH' on an OPEN statement."
    character(len=256), parameter :: message_152 = "ACCESS='DIRECT' is specified on an OPEN statement for a " // &
        "file that can only be accessed sequentially."
    character(len=256), parameter :: message_153 = "POSITION='REWIND' or POSITION='APPEND' is specified on an " // &
        "OPEN statement and the file is a pipe."
    character(len=256), parameter :: message_156 = "Invalid value for RECL= specifier on an OPEN statement."
    character(len=256), parameter :: message_159 = "External file input could not be flushed because the " // &
        "associated device is not seekable."
    character(len=256), parameter :: message_163 = "Multiple connections to a file located on a non-random " // &
        "access device are not allowed."
    character(len=256), parameter :: message_164 = "Multiple connections with ACTION='WRITE' or ACTION='READWRITE' are not allowed."
    character(len=256), parameter :: message_165 = "The record number of the next record that can be read or " // &
        "written is out of the range of the variable specified with the NEXTREC= specifier of the INQUIRE statement."
    character(len=256), parameter :: message_183 = "The maximum record length for the unit is out of the range " // &
        "of the scalar variable specified with the RECL= specifier in the INQUIRE statement."
    character(len=256), parameter :: message_184 = "The number of bytes of data transmitted is out of the range " // &
        "of the scalar variable specified with the SIZE= or NUM= specifier in the I/O statement."
    character(len=256), parameter :: message_186 = "Unit numbers must be between 0 and 2,147,483,647."
    character(len=256), parameter :: message_187 = "NAMELIST comments are not allowed by the Fortran 90 standard."
    character(len=256), parameter :: message_191 = "The RECL= specifier is specified on an OPEN statement that has ACCESS='STREAM'."
    character(len=256), parameter :: message_192 = "The value of the file position is out of the range of the " // &
        "scalar variable specified with the POS= specifier in the INQUIRE statement."
    character(len=256), parameter :: message_193 = "The value of the file size is out of the range of the scalar " // &
        "variable specified with the SIZE= specifier in the INQUIRE statement."
    character(len=256), parameter :: message_194 = "The BACKSPACE statement specifies a unit connected for unformatted stream I/O."
    character(len=256), parameter :: message_195 = "POS= specifier on an I/O statement is less than one."
    character(len=256), parameter :: message_196 = "The stream I/O statement cannot be performed on the unit " // &
        "because the unit is not connected for stream access."
    character(len=256), parameter :: message_197 = "POS= specifier on an I/O statement for a unit connected to a non-seekable file."
    character(len=256), parameter :: message_198 = "Stream I/O statement on an unconnected unit."
    character(len=256), parameter :: message_199 = "STREAM is not a valid value for the ACCESS= specifier on " // &
        "an OPEN statement in Fortran 90 or Fortran 95."

    character(len=256), dimension(112) :: messages = &
        (/ message_m004, message_m002, message_m001, message_001, message_002, message_003, &
           message_004, message_005, message_006, message_007, message_008, message_009, &
           message_010, message_011, message_012, message_013, message_014, message_015, &
           message_016, message_017, message_018, message_019, message_020, message_021, &
           message_022, message_023, message_024, message_025, message_026, message_027, &
           message_028, message_029, message_030, message_031, message_032, message_033, &
           message_034, message_036, message_037, message_038, message_039, message_040, &
           message_041, message_042, message_043, message_044, message_045, message_046, &
           message_047, message_048, message_049, message_053, message_056, message_058, &
           message_084, message_085, message_086, message_087, message_088, message_090, &
           message_092, message_093, message_094, message_095, message_096, message_097, &
           message_098, message_107, message_110, message_120, message_121, message_122, &
           message_125, message_127, message_128, message_129, message_130, message_131, &
           message_132, message_133, message_134, message_135, message_136, message_137, &
           message_138, message_139, message_140, message_141, message_142, message_144, &
           message_145, message_151, message_152, message_153, message_156, message_159, &
           message_163, message_164, message_165, message_183, message_184, message_186, &
           message_187, message_191, message_192, message_193, message_194, message_195, &
           message_196, message_197, message_198, message_199 /)

    contains

    subroutine i_retrieve_io_error_message(code, msg)
        implicit none

        integer, intent(in) :: code
        integer(8) :: lcode
        integer(bd) :: loc
        character(len=256), intent(out) :: msg

        lcode = int(code, kind=8)

        ! Get the location from the list of locations
        loc = locs(code)
        if (loc .eq. -1) then
            msg = 'No matching error message found for code.'
        else
            msg = messages(loc)
        endif
    end subroutine
    subroutine l_retrieve_io_error_message(code, msg)
        implicit none

        integer(8), intent(in) :: code
        integer(bd) :: loc
        character(len=256), intent(out) :: msg

        ! Get the location from the list of locations
        loc = locs(code)
        if (loc .eq. -1) then
            msg = 'No matching error message found for code.'
        else
            msg = messages(loc)
        endif
    end subroutine
end module io_messages
