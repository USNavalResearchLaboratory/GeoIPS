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

.PHONY: fields fields_plot fields_coverage
fields: init $(LIB)/fields.py $(LIB)/fields_plot.py $(LIB)/fields_coverage.py
fields_plot: $(LIB)/fields_plot.py
fields_coverage: $(LIB)/fields_coverage.py

$(LIB)/fields.py: $(SRC)/fields/fields.py init $(SRC)/fields/__init__.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).fields import fields"
	@echo "----------------------------------"
	@echo ""

$(LIB)/fields_plot.py: $(SRC)/fields/fields_plot.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).fields_plot import fields_plot"
	@echo "----------------------------------"
	@echo ""

$(LIB)/fields_coverage.py: $(SRC)/fields/fields_coverage.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).fields_coverage import fields_coverage"
	@echo "----------------------------------"
	@echo ""


.PHONY: clean_fields
clean_fields:
	@echo ""
	@echo "----------------------------------"
	@echo "Cleaning fields"
	@echo ""
	-rm $(LIB)/fields.py
	-rm $(LIB)/fields_plot.py
	-rm $(LIB)/fields_coverage.py
	$(DELIMPORT) "from .$(notdir $(LIB)).fields import fields"
	$(DELIMPORT) "from .$(notdir $(LIB)).fields_plot import fields_plot"
	$(DELIMPORT) "from .$(notdir $(LIB)).fields_coverage import fields_coverage"
	@echo "----------------------------------"
