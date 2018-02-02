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

SRCFILES := $(SRC)/init/__init__.py $(SRC)/init/add_import.py $(SRC)/init/del_import.py
INITFILES := $(LIB)/__init__.py $(INSTALLDIR)/__init__.py $(DOC)/source/geoalgs_modules.txt
ADDIMPORT := python $(LIB)/init/add_import.py $(INSTALLDIR)/__init__.py
DELIMPORT := python $(LIB)/init/del_import.py $(INSTALLDIR)/__init__.py
MODULEDOC := python $(LIB)/init/module_doc.py $(DOC)

init: $(INITFILES) $(LIB)/init

$(LIB)/init: $(SRCFILES)
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	-ln -s $(<D) $@
	@echo "----------------------------------"

$(LIB)/__init__.py: $(MODULEFILES)
	touch $@

$(INSTALLDIR)/__init__.py: $(MODULEFILES)
	@echo "Creating init in $(INSTALLDIR)"
	python $(SRC)/init/create_init.py $(INSTALLDIR)/__init__.py

$(DOC)/source/geoalgs_modules.txt: $(MODULEFILES)
	cp $(SRC)/init/geoalgs_modules_template.txt $@

.PHONY: clean_init
clean_init: $(MODULECLEAN)
	@echo ""
	@echo "----------------------------------"
	@echo "Cleaning Init"
	@echo ""
	-rm $(LIB)/init
	-rm $(INITFILES)
	@echo "----------------------------------"
