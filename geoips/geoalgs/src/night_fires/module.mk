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

# Please see geoalgs/README.txt for information on module/product naming (and everything else
# relating to geoalgs)

.PHONY: night_fires
night_fires: init $(LIB)/night_fires.py

NFIMP := "from .$(notdir $(LIB)).night_fires import night_fires"

$(LIB)/night_fires.py: $(SRC)/night_fires/night_fires.py config
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) $(NFIMP)
	@echo "----------------------------------"
	@echo ""

.PHONY: clean_night_fires
clean_night_fires:
	@echo ""
	@echo "----------------------------------"
	@echo "Cleaning night_fires"
	@echo ""
	-rm $(LIB)/night_fires.py
	$(DELIMPORT) $(NFIMP)
	@echo "----------------------------------"
