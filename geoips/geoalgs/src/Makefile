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

.SUFFIXES: .f90 .F90
.PHONY: all clean
.DEFAULT_GOAL := all

vpath %.h $(INC)
vpath %.so $(LIB)

#Define functions
define getobj
$(patsubst $1/%.f90,%.o, $(filter $1/%.f90,$2))
endef

define findmods
$(shell grep MODULE *.[fF]90)
endef

#Wraps a path into multiple lines for use in config file
define wrappath
''$(foreach d,$(subst /, ,$1),//\&\\n\\t\\t'/$(strip $(d))')
endef

#Define paths
ifndef LIB
    LIB = ../lib
endif
ifndef BIN
    BIN = ../bin
endif
#ifndef SRC
#    SRC = .
#endif
ifndef INC
    INC = ../include
endif
ifndef DOC
    DOC = ../docs
endif

#Set up FTP script
FTP = bash $(INSTALLDIR)/utils/ftp_in_make.sh

# Paths for source, implicitly list, don't explicitly include in Makefile.
# This allows you to add and remove packages just by getting rid of their 
# directory, and not having to modify any additional files.
# (so geoimg/geoimg.py and geoalgs/src/Makefile can be standard, regardless
# 	of a developers current set of packages).

# do a wildcard list of directories (*/ lists only directories),
#	then get rid of the / (module names do not have the '/' in them !)
# See geoalgs/README.txt for additional information on naming 
# packages.
SKIP_MODULES =
SKIP_MODULES += satsuncalc
SKIP_MODULES += interp
SKIP_MODULES += share
SKIP_MODULES += ccbg
SKIP_MODULES += geocolor_night
# SKIP_MODULES += elevation
MODULES = $(filter-out $(SKIP_MODULES),$(subst /,,$(wildcard */)))
# MODULES = $(subst /,,$(wildcard */))

#Module level make information is contained in module.mk files
MODULEFILES := $(patsubst %,%/module.mk,$(MODULES))
MODULECLEAN := $(patsubst %,clean_%,$(MODULES))
VPATH := $(LIB) . $(MODULES)
.PHONY: $(MODULES)

#Fortran compiler
# LOCALFORTANLIB, LOCALFORTRANINC, and FORTRANLIBS 
# are environment variables set in config shrc scripts.
# Default to paths of $FCNAME in top level make if not defined.
FLIBS = -L. -L${LOCALFORTRANLIB} ${FORTRANLIBS}
FINCS = -I. -I$(INC) -I${LOCALFORTRANINC} #$(patsubst %,-I%,$(MODULES))
# FFLAGS = -Wall -fPIC -O3 -fopenmp -J$(INC) $(FLIBS) $(FINCS)
FFLAGS = -Wall -fPIC -O3 -J$(INC) $(FLIBS) $(FINCS)
#f2py compiler
F2PC = f2py
#F2PCFLAGS = --fcompiler=$(FCNAME) --f90flags='-fopenmp' -lgomp --quiet --opt="-O3" $(FLIBS) $(FINCS)
F2PCFLAGS = --fcompiler=$(FCNAME) --quiet --opt="-O3" $(FLIBS) $(FINCS)
#Macros
AR = ar
ARFLAGS = rv
RM = rm -f
RMDIR = rmdir

#Variables that build as we include more module.mk files
SKIP :=
EXTRACLEAN :=

#Include all module.mk files from our modules
include $(MODULEFILES)
SKIP := skip: $(SKIP) :

all: $(MODULES)

#*********************************************
# HAVE QUIT USING MODULE LEVEL CLEAN TARGETS
# Just deleting bin, include, and lib in
# top-level Makefile
# Just keeping this because it does work and
# we may want to switch back in the future
#*********************************************
##Really need to figure out how to do this package by package
##May require lists of what each package builds
#clean: clean_rayleigh
#	-$(RM) `find $(INSTALLDIR) -type d -name "*.pyc"`
#	-$(RMDIR) $(BIN) $(LIB) $(INC)
#
##This generic clean rule will attempt to delete any files mentioned in the following variables:
##	packagenameFILES
##	packagenameOBJ
##	packagenameLIB
##	packagenameBIN
##Additionally, it will look for any .mod files in $(INC) whose stem is the same as
##	a file mentioned in packagenameOBJ
#clean_%:
#	#$(RM) $(INSTALLDIR)/docs/source/$*.rst
#	$(RM) $($(*)FILES) $($(*)OBJ) $(patsubst %.o, $(INC)/%.mod, $($(*)OBJ)) $($(*)LIB) $($(*)BIN)

#*********************************************
# IMPLICIT RULES
#*********************************************
#%: %.o
#	$(FC) -o %@ $(FFLAGS) $^

%.o:%.mod

%.o:%.f90
	$(FC) -c $(FFLAGS) $<

%.f90:%.F90
	$(FC) -E $(FFLAGS) $< -cpp -o $@

%.mod: %.f90 %.o
	@true

%.mod: %.F90 %.o
	@true

%.a:
	@echo
	@echo **********************************
	@echo Building archive: $@ with $?.  Command == $(AR)
	$(AR) $(ARFLAGS) $@ $?
	@echo **********************************
	@echo

lib%.so: %.f90
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	$(F2PC) $(F2PCFLAGS) -m lib$* $(SKIP) -c $?
	#@echo Linking $(SRC)/$@ to $(LIB)/$@
	mv $(SRC)/$(@F) $(LIB)
	@echo "----------------------------------"
	@echo ""

lib%.so: %.F90
	@echo ""
	@echo "----------------------------------"
	@echo Making library: $@
	$(F2PC) $(F2PCFLAGS) -m lib$* $(SKIP) -c $?
	#@echo Linking $(SRC)/$@ to $(LIB)/$@
	mv $(SRC)/$(@F) $(LIB)
	@echo "----------------------------------"
	@echo ""

.PHONY: clean
clean: $(MODULECLEAN)
	@echo ""
	@echo ""
	@echo ""
	@echo "DONE WITH PACKAGES"
	@echo "$(MODULECLEAN)"
	@echo ""
	@echo ""
	@echo ""
