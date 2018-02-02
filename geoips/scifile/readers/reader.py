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

# Python Standard Libraries
import os
import inspect

class Reader(object):

    def __call__(self, fname, datavars, gvars, metadata, chans=None, sector_definition=None,
                 self_register=False):
        if self_register:
            return self.read(fname, datavars, gvars, metadata, chans=chans, sector_definition=sector_definition,
                         self_register=self_register)
        else:
            # There is probably a better way to handle varying def read call signatures (kwargs ?), but 
            # for now, only try to pass self_register if it is true, since only abi and ahi readers have
            # it defined.
            return self.read(fname, datavars, gvars, metadata, chans=chans, sector_definition=sector_definition)

    @property
    def name(self):
        return str(self.__class__)

    @staticmethod
    def format_test(fname):
        raise NotImplementedError(inspect.stack()[0][3])

    @staticmethod
    def read(fname,chans=None):
        raise NotImplementedError(inspect.stack()[0][3])

