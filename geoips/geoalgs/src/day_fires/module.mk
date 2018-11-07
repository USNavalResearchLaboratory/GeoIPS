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

.PHONY: day_fires
day_fires: $(LIB)/day_fires.py

$(LIB)/day_fires.py: $(SRC)/day_fires/day_fires.py config init
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	@echo $(MODULES)
	
	-ln -s $< $(LIB)
	$(ADDIMPORT) "from .$(notdir $(LIB)).day_fires import day_fires"
	@echo "----------------------------------"
	@echo ""

.PHONY: clean_day_fires
clean_day_fires:
	@echo ""
	@echo "----------------------------------"
	@echo "Cleaning day_fires"
	@echo ""
	-rm $(LIB)/day_fires.py
	$(DELIMPORT) "from .$(notdir $(LIB)).day_fires import day_fires"
	@echo "----------------------------------"
