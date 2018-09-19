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

.PHONY: extalg extalg_plot extalg_coverage
extalg: init $(LIB)/extalg.py $(LIB)/extalg_plot.py $(LIB)/extalg_coverage.py
extalg_plot: $(LIB)/extalg_plot.py
extalg_coverage: $(LIB)/extalg_coverage.py

$(LIB)/extalg.py: $(SRC)/extalg/extalg.py init $(SRC)/extalg/__init__.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	@echo Creating extalg_config.py
	@echo "def extalg_config(sat_config):" > $(SRC)/extalg/extalg_config.py
	@cat $(SRC)/extalg/extalg_config_*.py >> $(SRC)/extalg/extalg_config.py
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).extalg import extalg"
	@echo "----------------------------------"
	@echo ""

$(LIB)/extalg_plot.py: $(SRC)/extalg/extalg_plot.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).extalg_plot import extalg_plot"
	@echo "----------------------------------"
	@echo ""

$(LIB)/extalg_coverage.py: $(SRC)/extalg/extalg_coverage.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).extalg_coverage import extalg_coverage"
	@echo "----------------------------------"
	@echo ""


.PHONY: clean_extalg
clean_extalg:
	@echo ""
	@echo "----------------------------------"
	@echo "Cleaning extalg"
	@echo ""
	-rm $(LIB)/extalg.py
	-rm $(LIB)/extalg_plot.py
	-rm $(LIB)/extalg_coverage.py
	$(DELIMPORT) "from .$(notdir $(LIB)).extalg import extalg"
	$(DELIMPORT) "from .$(notdir $(LIB)).extalg_coverage import extalg_coverage"
	$(DELIMPORT) "from .$(notdir $(LIB)).extalg_plot import extalg_plot "
	@echo "----------------------------------"
