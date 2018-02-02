#!/usr/bin/env python

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


__doc__ = '''
          Exception classes for use with the sectorfile module.
          :docnote:`Terrible documentation here.  Did not check actual uses.`
          '''

class SectorFileError(Exception):
    __doc__ = '''
              Exception class to be raised when there is an error in reading
              a sectorfile.
              '''
class SFAttributeError(SectorFileError):
    __doc__ = '''
              Exception class to be raised when there is an error in reading
              a sectorfile's attribute.
              '''
