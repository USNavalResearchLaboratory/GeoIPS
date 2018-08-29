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

.PHONY: geo_stitched geo_stitched_plot geo_stitched_coverage geo_stitched_config
geo_stitched: init $(LIB)/geo_stitched.py $(LIB)/geo_stitched_plot.py $(LIB)/geo_stitched_coverage.py $(LIB)/geo_stitched_config.py
geo_stitched_plot: $(LIB)/geo_stitched_plot.py
geo_stitched_coverage: $(LIB)/geo_stitched_coverage.py
geo_stitched_config: $(LIB)/geo_stitched_config.py

$(LIB)/geo_stitched.py: $(SRC)/geo_stitched/geo_stitched.py init $(SRC)/geo_stitched/__init__.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).geo_stitched import geo_stitched"
	@echo "----------------------------------"
	@echo ""

$(LIB)/geo_stitched_plot.py: $(SRC)/geo_stitched/geo_stitched_plot.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).geo_stitched_plot import geo_stitched_plot"
	@echo "----------------------------------"
	@echo ""

$(LIB)/geo_stitched_coverage.py: $(SRC)/geo_stitched/geo_stitched_coverage.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).geo_stitched_coverage import geo_stitched_coverage"
	@echo "----------------------------------"
	@echo ""

$(LIB)/geo_stitched_config.py: $(SRC)/geo_stitched/geo_stitched_config.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).geo_stitched_config import geo_stitched_config"
	@echo "----------------------------------"
	@echo ""


.PHONY: clean_geo_stitched
clean_geo_stitched:
	@echo ""
	@echo "----------------------------------"
	@echo "Cleaning geo_stitched"
	@echo ""
	-rm $(LIB)/geo_stitched.py
	-rm $(LIB)/geo_stitched_plot.py
	-rm $(LIB)/geo_stitched_coverage.py
	-rm $(LIB)/geo_stitched_config.py
	$(DELIMPORT) "from .$(notdir $(LIB)).geo_stitched import geo_stitched"
	$(DELIMPORT) "from .$(notdir $(LIB)).geo_stitched_plot import geo_stitched_plot"
	$(DELIMPORT) "from .$(notdir $(LIB)).geo_stitched_coverage import geo_stitched_coverage"
	$(DELIMPORT) "from .$(notdir $(LIB)).geo_stitched_config import geo_stitched_config"
	@echo "----------------------------------"
