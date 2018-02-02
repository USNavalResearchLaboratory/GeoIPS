#!/bin/evn python

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


# Installed Libraries
from IPython import embed as shell

class XMLNode(object):
    '''Class for handling nodes with children from a sectorfile.'''
    def __init__(self, node):
        self.node = node

    def __getattr__(self, item):
        '''Overridden from base object class.  Will attempt to look for an instance
        attribute.  If it is not found, will attempt to look in the XML for a matching
        element.  The XML is located in self.node.  If still not found, will raise an
        AttributeError.'''
        try:
            #Test to see if this attribute is an instance attribute
            return object.__getattr__(self, item)
        except AttributeError:
            if not hasattr(self, 'node'):
                raise
            #If it was not found, check in the XML
            return self.node.find(item).pyval

    def __setattr__(self, item, value):
        '''Overridden from base object class.  If self.__initialized has not yet been set
        will use object.__setattr__().  If self.__initialized has been set, will check to
        be sure that the XML contains the appropriate tag, then set the text for that
        tag in the XML (located in self.node).  If an appropriate element was not found in
        the XML, will attempt to use object.__setattr__() to set an instance attribute.
        '''
        #Only try to access XML nodes if we actually have an XML tree to work with
        if hasattr(self, 'node') and hasattr(self.node, item):
            self.node[item] = value
        return object.__setattr__(self, item, value)
