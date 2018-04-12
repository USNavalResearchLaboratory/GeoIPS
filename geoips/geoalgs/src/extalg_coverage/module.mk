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

.PHONY: extalg_coverage
extalg_coverage: config init $(LIB)/extalg_coverage.py 

$(LIB)/extalg_coverage.py: $(SRC)/extalg_coverage/extalg_coverage.py config init $(SRC)/extalg_coverage/__init__.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	@echo "----------------------------------"
	@echo ""
	$(ADDIMPORT) "from .$(notdir $(LIB)).extalg_coverage import extalg_coverage"


.PHONY: clean_extalg_coverage
clean_extalg_coverage:
	@echo ""
	@echo "----------------------------------"
	@echo "Cleaning extalg_coverage"
	@echo ""
	-rm $(LIB)/extalg_coverage.py
	$(DELIMPORT) "from .$(notdir $(LIB)).extalg_coverage import extalg_coverage"
	@echo "----------------------------------"
