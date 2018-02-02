#!/bin/env python

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

class DownloaderTimeout(Exception):
    'Exception raised by downloaders when a timeout is experienced.'
    def __init__(self, msg):
        self.value = msg
    def __str__(self):
        return self.value

class DownloaderGiveup(Exception):
    'Exception raised when a downloader gives up; typically due to timeouts.'
    def __init__(self, msg):
        self.value = msg
    def __str__(self):
        return self.value

class DownloaderFailed(Exception):
    'Exception raised when a downloader fails; typically due to wrong data_type / host_type pair.'
    def __init__(self, msg):
        self.value = msg
    def __str__(self):
        return self.value
