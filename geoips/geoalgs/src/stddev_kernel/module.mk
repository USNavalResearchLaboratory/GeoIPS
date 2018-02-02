
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

stddev_kernel: init libstddev_kernel.so
	$(MODULEDOC) $(DOC)/stddev_kernel
	$(ADDIMPORT) "from .$(notdir $(LIB)).libstddev_kernel import stddev_kernel" --fortran

libstddev_kernel.so: stddev_kernel.f90 config.o

.PHONY: clean_stddev_kernel
clean_stddev_kernel:
	@echo ""
	@echo "----------------------------------"
	@echo "Cleaning Stddev_kernel"
	@echo ""
	-rm $(LIB)/libstddev_kernel.so
	$(DELIMPORT) "from .$(notdir $(LIB)).libstddev_kernel import stddev_kernel" --fortran
	@echo "----------------------------------"
