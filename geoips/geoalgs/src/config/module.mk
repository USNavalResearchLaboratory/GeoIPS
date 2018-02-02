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

CONFIGIMP := "from .$(notdir $(LIB)).libconfig import config" --fortran

#Wraps a path into multiple lines for use in config file
define wrappath
''$(foreach d,$(subst /, ,$1),//\&\\n        '/$(strip $(d))')
endef

config: init libconfig.so config.o
	$(ADDIMPORT) $(CONFIGIMP)

libconfig.so: config.f90 config.h

config.o: config.f90 config.h

config.h: $(SRC)/config/config_template.h
	cp $< $(INC)/$@
	sed -i "s,<install_path>,$(call wrappath,$(INSTALLDIR)),g" $(INC)/$@
	sed -i "s,<ancildat_path>,$(call wrappath,$(ANCILDATDIR)),g" $(INC)/$@
	sed -i "s,<bin_path>,$(call wrappath,$(BIN)),g" $(INC)/$@
	sed -i "s,<lib_path>,$(call wrappath,$(LIB)),g" $(INC)/$@
	sed -i "s,<inc_path>,$(call wrappath,$(INC)),g" $(INC)/$@
	sed -i "s,<src_path>,$(call wrappath,$(SRC)),g" $(INC)/$@

.PHONY: clean_config
clean_config:
	@echo ""
	@echo "----------------------------------"
	@echo "Cleaning Config"
	@echo ""
	-rm $(LIB)/libconfig.so
	#-rm $(INC)/config.f90
	$(DELIMPORT) $(CONFIGIMP)
	@echo "----------------------------------"
