# Author:
#    Naval Research Laboratory, Marine Meteorology Division
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the NRLMMD License included with this program.  If you did not
# receive the license, see http://www.nrlmry.navy.mil/geoips for more
# information.
#
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# included license for more details.

UTILSIMP := "from .$(notdir $(LIB)).liberror_codes import error_codes"

utils: liberror_codes.so datetime_utils.o errors.o init
	$(ADDIMPORT) $(UTILSIMP)


liberror_codes.so: error_codes.f90 io_messages.o errors.o config.o

# ERRORS
newunit.o: newunit.f90
normalize.o: normalize.o clip.o
string_operations.o: string_operations.f90
datetime_utils.o: datetime_utils.f90
errors.o: errors.f90 io_messages.o error_codes.o config.o
error_codes.o: error_codes.f90 config.o io_messages.o
io_messages.o: io_messages.f90 config.o
#error_codes.o: io_messages.o
percentile.o: percentile.f90 mrgrnk.o
datetime_utils.o: datetime_utils.f90 config.o

.PHONY: clean_utils
clean_utils:
	@echo ""
	@echo "----------------------------------"
	@echo "Cleaning Utils"
	@echo ""
	-rm $(LIB)/liberror_codes.so
	$(DELIMPORT) $(UTILSIMP)
	@echo "----------------------------------"
