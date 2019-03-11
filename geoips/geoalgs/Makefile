.PHONY: all clean install

#SET THIS BEFORE DOING ANYTHING!!!  Choices are NRL and FNMOC
DEFAULT_COMPILER = gnu

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

#This is the top-level Makefile for compiling fortran source
#	related to GeoIPS.
#
#The process used here for make is dynamic.  Each directory under
#	./src that contains a module.mk file is considered to be a
#	separate target by ./src/Makefile.  ./src/Makefile will "include"
#	each module.mk file, causing its instructions to be executed.
#	This provides us with the ability to easily extend the set of
#	fortran packages to be compiled.

#Get the path to this makefile so that we can find the source
SOURCEDIR = $(shell pwd)

#Get the current working directory.  Will be installed there.
INSTALLDIR = $(shell pwd)
# Tried installing from GeoIPS_nrl to GEOALGS_BUILD_PATH.
# Going in the direction of just linking everything from EXTERNAL_GEOALGSPATH
# into $GEOIPS, and building directly from GeoIPS to itself.  But I know
# changing the INSTALLDIR will work if needed in the future.
#INSTALLDIR = $(GEOALGS_BUILD_PATH)

#Set variables for the build location
#Everything will go to the current working directory
SRC = $(SOURCEDIR)/src
LIB = $(INSTALLDIR)/lib
BIN = $(INSTALLDIR)/bin
INC = $(INSTALLDIR)/include
ifeq ($(GEOALGSDATA),)
    ANCILDATDIR = $(INSTALLDIR)/dat
else
    ANCILDATDIR = $(GEOALGSDATA)
endif

#VPATH = $(VPATH):$(LIB):$(INC)
VPATH =

PYTHONPATH := $(PYTHONPATH):$(INSTALLDIR)

#Default to use gfortran compiler
#ifeq ($(FC),f77)
#    override FC = gfortran
#endif
##Set up compiler specific variables
#ifeq ($(FC),gfortran)
#    FCNAME = gfortran
#else ifeq ($(FC),intel)
#    override FC = ifort
#    FCNAME = intelem
#else
#    $(error Compiler not recognized $(FC).  Currently accepts either gfortran or intel.)
#endif
FC = ifort
FCNAME = intelem
#FC = gfortran
#FCNAME = gnu95

# Set fortran paths
ifndef LOCALFORTRANLIB
	LOCALFORTRANLIB = $(shell dirname `dirname \`which $(FC)\``)/lib
endif
ifndef LOCALFORTRANINC
	LOCALFORTRANINC = $(shell dirname `dirname \`which $(FC)\``)/include
endif

#Note: $(MAKECMDGOALS) is an automatic variable that stores the goals entered
#	when calling make at command line.  So, if called like this:
#		make install rayleigh
#	$(MAKECMDGOALS) would hold:
#		install rayleigh.
#	If, however, make is called with no arguments then $(MAKECMDGOALS) will be
#	empty and must be initialized to contain "all" in order to act upon the
#	"all" rule in src/Makefile

#Determine which compiler to use
COMPILERS = gnu intel
COMPILER := $(filter $(COMPILERS), $(MAKECMDGOALS))
ifeq ($(COMPILER),)
    COMPILER = $(DEFAULT_COMPILER)
endif
ifeq ($(COMPILER),gnu)
    FC = gfortran
    FCNAME = gfortran
else ifeq ($(COMPILER),intel)
    FC = ifort
    FCNAME = intelem
else
    $(error Complier not recognized $(FC).  Currently accepts $(COMPILERS))
endif

#Determine if we want to clean
ifneq (,$(findstring clean, $(MAKECMDGOALS)))
    DOCLEAN = clean
else
    DOCLEAN =
endif

#Create goals variable for src/Makefile by removing "install" from goals list
SRCMAKECMDGOALS := $(filter-out $(COMPILER),$(filter-out clean, $(MAKECMDGOALS)))

#If the new goals list is empty, then set to "all" and append "all" to
#	current goals list in $(MAKECMDGOALS)
ifeq ($(strip $(SRCMAKECMDGOALS)),)
    SRCMAKECMDGOALS := all
endif
override MAKECMDGOALS = $(SRCMAKECMDGOALS) $(DOCLEAN)

#Variables to be passed to child make processes
MAKEVARS = -e LIB=$(LIB) -e BIN=$(BIN) -e SRC=$(SRC) -e INC=$(INC) -e ANCILDATDIR=$(ANCILDATDIR) \
		   -e FCNAME=$(FCNAME) -e INSTALLDIR=$(INSTALLDIR) -e SOURCEDIR=$(SOURCEDIR) \
		   -e LOCALFORTRANINC=$(LOCALFORTRANINC) -e LOCALFORTRANLIB=$(LOCALFORTRANLIB) #\
		   #-e VPATH=$(VPATH)

#Target here is all goals other than "install"
# Don't need to make ANCILDATDIR (should already exist) and it breaks installation in Docker
#Calling make with -C means CD to that directory
#Calling make with -e <cmd> execute cmd before the rest of the make script
# $(COMPILER) $(SRCMAKECMDGOALS): $(LIB) $(BIN) $(SRC) $(INC) $(ANCILDATDIR)
.PHONY: $(COMPILER) $(SRCMAKECMDGOALS)
$(COMPILER) $(SRCMAKECMDGOALS): $(LIB) $(BIN) $(SRC) $(INC)
	@echo ""
	@echo "Installing from $(SOURCEDIR)"
	@echo "Installing in $(INSTALLDIR)"
	@echo "--------------------------------------------------"
	@echo "Building geoalgs library using $(COMPILER) compiler."
	@echo "Written by: Naval Research Laboratory,"
	@echo "            Marine Meteorology Division"
	@echo "            http://www.nrlmry.navy.mil/geoips"
	@echo "Current settings:"
	@echo "    Fortran Compiler:   $(FC)"
	@echo "    F2PY Compiler Name: $(FCNAME)"
	@echo "    Build Targets:      $(SRCMAKECMDGOALS)"
	@echo "    Ancildat Dir:      $(ANCILDATDIR)"
	@echo "--------------------------------------------------"
	@echo ""
	#Build modules
	make FC=$(FC) $(MAKEVARS) -C $(SOURCEDIR)/src $(SRCMAKECMDGOALS)
	#Build docs
	make -C $(INSTALLDIR)/docs -f $(INSTALLDIR)/docs/Makefile html

#.PHONY: docs
#docs: $(INSTALLDIR)/docs/build/html
#
#$(INSTALLDIR)/docs/build/html: $(INSTALLDIR)/docs/source/index.rst $(SRCMAKECMDGOALS)

$(LIB):
	mkdir $(LIB)

$(BIN):
	mkdir $(BIN)

$(INC):
	mkdir $(INC)

# $(ANCILDATDIR):
# 	mkdir $(ANCILDATDIR)

.PHONY: clean
clean:
	-make $(MAKEVARS) -C $(INSTALLDIR)/src -f $(SRC)/Makefile clean
	# -make $(MAKEVARS) -C $(INSTALLDIR)/docs -f $(DOC)/Makefile clean
	# from jeremy 5MAR19
	-make $(MAKEVARS) -C $(INSTALLDIR)/docs -f $(INSTALLDIR)/docs/Makefile clean
	-rm -f $(SRC)/*.o $(SRC)/*.so
	-rm -f $(BIN)/* $(INC)/*
	-find $(SOURCEDIR) -type f -name "*.pyc" -exec rm {} \;
	-rmdir $(BIN) $(LIB) $(INC)
