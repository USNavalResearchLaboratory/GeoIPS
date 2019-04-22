geoalgs Package
===============

:mod:`geoalgs` is a set of packages intended to apply various corrections to satellite data.
Most of the code provided is written in `fortran90` and compiled using `numpy.f2py`
in order to create dynamic libraries that can be used by Python as modules.
Although some special steps were taken in order to prepare each package for
f2py, each package is useable as a pure fortran90 package.

Configuring :mod:`geoalgs`
--------------------------
While most configuration is taken care of automatically in the build process, there are
a couple of configuration issues that need to be taken care of prior to building :mod:`geoalgs`.

First, in `geoalgs/Makefile` on line #4 the IAM variable must be set to either "nrl" or "fnmoc"
depending on where the system is being built.  Currently only "nrl" and "fnmoc" are handled.
It is hoped that this can be automated at a later date.

Second, there are preprocessor directives in several F90 files that must be set up for
any new user of the package.  These directives set the names for the channels for the
VIIRS and MODIS sensors to conform to the user's conventions.  The following files must be
edited:

* src/bldust/viirs_rayleigh_constants.F90
* src/bldust/modis_rayleigh_constants.F90
* src/bldust/viirs_bldust_constants.F90
* src/bldust/modis_bldust_constants.F90

Building :mod:`geoalgs`
-----------------------
Building this package is as simple as calling "make" in the top level directory.
To install in a different location, simply change directories to the location
at which you wish to install the software, then run "<path_to_package>/make".
All required directories will be created in the current directory including
bin, include, and lib.  Please note the warning below.

.. warning::
    Before building this package, the user should be warned that the "clean" target
    in the Makefile is currently naive and dangerous.  If "make clean" is run in
    a directory that contains directories named "bin", "include", or "lib", the
    contents of those directories, as well as the directories themselves, may be lost.
    To avoid this, it is likely better, at present, to build this package in a directory
    of its own.  It is intended that this will be fixed in the future and is a consequence
    of the "smart" make procedures, where not all files produces are known a prioi.  

Importing :mod:`geoalgs`
------------------------
:mod:`geoalgs` can be imported in Python using the same syntax as any other Python package:

.. code-block:: python

    import geoalgs

Individual modules can be imported using:

.. code-block:: python

    from geoalgs import rayleigh

.. include:: geoalgs_modules.txt

Preparation for f2py:
---------------------
f2py is a parser for fortran90 code that is able to produce dynamic libraries that expose hooks for
python to grab onto.  These hooks allow python to import any exposed `subroutines` as if they were
python modules.  There are a few caveats to how code must be written when used with f2py.

Typically in fortran90 we are able to make use of the `allocate` statement to handle dynamic array sizes.
When using f2py, however, this is not possible.  All `allocate` statements must be stripped out of the code.
Rather than relying on `allocate` we must provide explicit dimension inputs.

Through some magic using f2py directives, these explicit dimension inputs can be optional in the Python
call signature.  f2py and Python are smart enough to figure out how big an array is and pass the
dimension sizes to the appropriate variables.

Additionally, `use` statements generally behave oddly when we attempt to expose anything from the used
module.  Will go into more detail on a workaround for this at a later date.
