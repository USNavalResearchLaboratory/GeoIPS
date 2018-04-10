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

.PHONY: extalg extalg_config
extalg: config init $(LIB)/extalg.py $(LIB)/extalg_config.py
extalg_config: $(LIB)/extalg_config.py

$(LIB)/extalg.py: $(SRC)/extalg/extalg.py config init $(SRC)/extalg/__init__.py
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

$(LIB)/extalg_config.py: $(SRC)/extalg/extalg_config.py
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	@echo Creating extalg_config.py
	@echo "def extalg_config(sat_config):" > $(SRC)/extalg/extalg_config.py
	@cat $(SRC)/extalg/extalg_config_*.py >> $(SRC)/extalg/extalg_config.py
	-ln -s $< $@
	$(ADDIMPORT) "from .$(notdir $(LIB)).extalg_config import extalg_config"
	@echo "----------------------------------"
	@echo ""

.PHONY: clean_extalg
clean_extalg:
	@echo ""
	@echo "----------------------------------"
	@echo "Cleaning extalg"
	@echo ""
	-rm $(LIB)/extalg.py
	-rm $(LIB)/extalg_config.py
	$(DELIMPORT) "from .$(notdir $(LIB)).extalg import extalg"
	$(DELIMPORT) "from .$(notdir $(LIB)).extalg_config import extalg_config"
	@echo "----------------------------------"
