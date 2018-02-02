Each package must contain a module.mk file
The module.mk file describes all dependencies within each package
The module.mk file must keep track of created files in the following variables for proper cleaning:
    packagenameOBJ
    packagenameLIB
    packagenameBIN
Top level modules must be added to the top level __init__.py
This is accomplished via the $(ADDIMPORT) variable which calls src/init/add_import.py
Note that for modules created from Fortran source, the --fortran option should be supplied
This will create a docstring in a format readable by sphinx for documentation creation
Some packages rely on the "config".  Should figure out how to force config to always build first.
Some packages rely on the "init" package.  Should be entered at the main target for each.
