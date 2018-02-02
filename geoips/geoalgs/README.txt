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

geoalgs is a set of packages intended to apply various corrections to satellite data.
Most of the code provided is written in fortran90 and compiled using numpy.f2py
in order to create dynamic libraries that can be used by Python as modules.
Although some special steps were taken in order to prepare each package for
f2py, each package is useable as a pure fortran90 package.

AVAILABLE ALGORITHMS:
    geoalgs.rayleigh - An atmospheric rayleigh scattering correction capable of correcting
                     MODIS (channels 1-4) and VIIRS (channels 3,4,5,7).
    geoalgs.lunarref - Produces approximate reflectance values for nighttime scenes
                     using the VIIRS Day/Night band.
    geoalgs.sunglint - Produces a boolean mask indicating the location of sunglint.
                     Used in the forthcoming Bluelight-Dust algorithm.

WARNING:
    Before building this package, the user should be warned that the "clean" target
    in the Makefile is currently naive and dangerous.  If "make clean" is run in
    a directory that contains directories named "bin", "include", or "lib", the
    contents of those directories, as well as the directories themselves, may be lost.
    To avoid this, it is likely better, at present, to build this package in a directory
    of its own.  It is intended that this will be fixed in the future and is a consequence
    of the "smart" make procedures, where not all files produces are known a prioi.  

BUILDING PACKAGE:
    Building this package is as simple as calling "make" in the top level directory.
    To install in a different location, simply change directories to the location
    at which you wish to install the software, then run "<path_to_package>/make".
    All required directories will be created in the current directory including
    bin, include, and lib.  Please note the above warning.

IMPORTING PACKAGE:
    The package can be imported in Python using the following syntax:
        import geoalgs
    Individual modules can be imported using:
        from geoalgs import <package_name>

PACKAGE / PRODUCT NAMING CONVENTIONS / REQUIREMENTS:
    A consistent product/package name MUST be used throughout:
        $GEOIPS/productfiles
        $GEOIPS/geoalgs/src

    Example:
    Module-Name product name to module_name geoalgs package

    $GEOIPS/productfiles/<platformname>/Module-Name.xml
        <product method='external' name='Module-Name'>
        ***Note capitalized first letters, and - between words.
            - will be automatically converted to ' ' on web.
            We use - in product names instead of _ because 
            product name goes in output filename, and sometimes
            we use _ as delimiter in product output filenames.
    $GEOIPS/geoalgs/src/module_name/module_name.py
        def module_name():
        *** Note all lower case (for portability to platforms
            that are case insensitive) and _ between words
            (because '-' is a minus sign in python!)
            The Module-Name in productfile is automatically 
            mapped one-to-one in geoimg/geoimg.py to the
            module_name in geoalgs. So they must match.
    $GEOIPS/geoalgs/src/module_name/__init__.py
        from module_name import module_name 
    $GEOIPS/geoalgs/src/module_name/module.mk
        *** Lots of 'module_name's in this file. Copy another module.mk 
            and just do a search and replace for old_module_name to 
            new_module_name. ie
        :%s,old_module_name,new_module_name,gc
        

    Consistent naming allows a one-to-one mapping from geoimg to geoalgs, 
    so we don't have to add the module name to 
        geoimg/geoimg.py
            algorithm = getattr(geoalgs,self.product.name.lower().replace('-','_'))
            *** automatically finds the appropriate geoalgs sub-package

        or
        geoalgs/src/Makefile
            MODULES = $(subst /,,$(wildcard */))
            *** automatically lists all package directories in geoalgs/src
                Note this means every subdirecory in geoalgs/src MUST have
                a module.mk and build successfully or you may break all 
                algorithms in geoalgs !!! (make will stop at the faulty package)
        

    NOTE Python style guides encourage module / filenames that are:
        all lower case (for portability to case insensitive platforms)
        all alphanum chars, '_' only when necessary (absolutely no '-'! That is a minus sign)
        relatively short name for portability to platforms that have line/filename length limits.

    We are going to additionally go with the convention of:
        '_' in module/file names that correspond directly to a product (ie, module_name->Module-Name)
        no '_' in module/file names that are algorithms that are only referenced by 
            other "wrapper" code and do not relate directly to a product, 
            ie elevation.py, rayleigh.py, iremissivity.py


AVAILABLE EXECUTABLES:
    There may be several available binary executables in geoalgs/bin.  These are not intended
    for use by either NRL or FNMOC.  They are intended for backwards compatability with
    CIRA's code base.

PACKAGE ORGANIZATION:
    bin:             Compiled executables.
                     These are primarily intended for backwards compatibility with
                     CIRA's code base and not intended for use by NRL or FNMOC.
                     They are provided for completeness.
    doc:             Readme files for the various packages
    giutils:         general use python utilities
    include:         compiled modules and headers
    lib:             compiled libraries (typically shared libraries)
    python_packages: python packages that interface with the compiled fortran libraries
                     can be used as examples of how to utilize the libraries
    src:             source code for the various packages 
                     includes static lookup tables and other data files

PREPARATION FOR F2PY:
    Typically in fortran90 we are able to make use of ALLOCATE statements to handle dynamic array sizes.
    When using f2py, however, this is not possible.  All ALLOCATEs must be stripped out of the code. As
    a consequence, there are more required inputs than would be typically expected.  For instance, "lines"
    and "stamples" are required inputs for some modules in order to determine the shape of the various
    input arrays.  Normally these values could be inferred and the arrays could be allocated dynamically,
    however, when using f2py, this is not possible and the values must be known a priori.

    Additionally, USE statements behave in an odd manner when nested.  For instance, assume we have the
    following setup:
        package.f90 <-- package_constants.f90 <-- constants.f90
    where package.f90 uses package_constants.f90 which uses constants.f90.  In this case, the contents
    of the constants module will be included in the package_constants which will be included in the
    package.  If, however, we attempt to compile package_constants.f90 into package_constants.so using
    f2py, then import from package_constants.so, the contents of constants.f90 will not be exposed to
    python.  To see a more complete description of the problem, please see the following issue on the
    numpy github repository:
        https://github.com/numpy/numpy/issues/3562
