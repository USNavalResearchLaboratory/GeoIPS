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

.PHONY: winds winds_plot winds_coverage
# NOTE $(LIB)/motion.py MUST be last so _coverage and _plot get linked first
winds: init $(LIB)/winds_plot.py $(LIB)/winds_coverage.py $(LIB)/winds.py
winds_plot: $(LIB)/winds_plot.py
winds_coverage: $(LIB)/winds_coverage.py

$(LIB)/winds.py: $(SRC)/winds/winds.py init
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	-ln -s $(SRC)/winds/*.py $(LIB)
	$(ADDIMPORT) "from .$(notdir $(LIB)).winds import winds"
	@echo "----------------------------------"
	@echo ""

$(LIB)/winds_plot.py: $(SRC)/winds/winds_plot.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).winds_plot import winds_plot"
	@echo "----------------------------------"
	@echo ""

$(LIB)/winds_coverage.py: $(SRC)/winds/winds_coverage.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).winds_coverage import winds_coverage"
	@echo "----------------------------------"
	@echo ""


.PHONY: clean_winds
clean_winds:
	@echo ""
	@echo "----------------------------------"
	@echo "Cleaning winds"
	@echo ""
	-rm $(LIB)/winds.py
	-rm $(LIB)/winds_plot.py
	-rm $(LIB)/winds_coverage.py
	$(DELIMPORT) "from .$(notdir $(LIB)).winds import winds"
	$(DELIMPORT) "from .$(notdir $(LIB)).winds_coverage import winds_coverage"
	$(DELIMPORT) "from .$(notdir $(LIB)).winds_plot import winds_plot "
	@echo "----------------------------------"
