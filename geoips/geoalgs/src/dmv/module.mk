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

.PHONY: dmv dmv_plot dmv_coverage
dmv: init $(LIB)/dmv.py $(LIB)/dmv_plot.py $(LIB)/dmv_coverage.py
dmv_plot: $(LIB)/dmv_plot.py
dmv_coverage: $(LIB)/dmv_coverage.py

$(LIB)/dmv.py: $(SRC)/dmv/dmv.py init $(SRC)/dmv/__init__.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).dmv import dmv"
	@echo "----------------------------------"
	@echo ""

$(LIB)/dmv_plot.py: $(SRC)/dmv/dmv_plot.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).dmv_plot import dmv_plot"
	@echo "----------------------------------"
	@echo ""

$(LIB)/dmv_coverage.py: $(SRC)/dmv/dmv_coverage.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).dmv_coverage import dmv_coverage"
	@echo "----------------------------------"
	@echo ""


.PHONY: clean_dmv
clean_dmv:
	@echo ""
	@echo "----------------------------------"
	@echo "Cleaning dmv"
	@echo ""
	-rm $(LIB)/dmv.py
	-rm $(LIB)/dmv_plot.py
	-rm $(LIB)/dmv_coverage.py
	$(DELIMPORT) "from .$(notdir $(LIB)).dmv import dmv"
	$(DELIMPORT) "from .$(notdir $(LIB)).dmv_coverage import dmv_coverage"
	$(DELIMPORT) "from .$(notdir $(LIB)).dmv_plot import dmv_plot "
	@echo "----------------------------------"
