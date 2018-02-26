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

# Python Standard Libraries
import os
import logging
from datetime import datetime
from datetime import timedelta

try:
    from IPython import embed as shell
except:
    print 'Failed import IPython in geoimg/plot/rgbimg.py. If you need it, install it.'

log = logging.getLogger(__name__)

COPYRIGHT = os.getenv('GEOIPS_COPYRIGHT')
if COPYRIGHT is None:
    COPYRIGHT = 'NRL-Monterey'


class Title(object):
    def __init__(self, lines=None, satellite=None, sensor=None, product=None, date=None,
                 start_time=None, end_time=None, copyright=COPYRIGHT, extra_lines=None, tau=None):
        '''
        Construct a title for GeoIPS imagery.

        If provided the ``lines`` keyword will override all other keywords and *explicitly*
        set the title.

        :docnote:`This routine should be cleaned up.  It works okay for now, but is not intuitive.
                  The lines keyword behaves in a very odd way.`

        Any combination of the other available keywords will produce a title of the form:

        >>> <satellite> <sensor> <product> YYYY/MM/DD HH:MM:SS[-HH:MM:SS]Z <copyright>
        >>> <extralines>[0]
        >>> <extralines>[1]
        >>> <extralines>[2]
        >>> .
        >>> .
        >>> .

        +-------------+--------+-----------------------------------------------------------+
        | Keyword:    | Type:  | Description:                                              |
        +=============+========+===========================================================+
        | lines       | *list* | A list of strings containing **all** lines to be included |
        |             |        | in the title.                                             |
        |             |        | If ``lines`` is provided, all other keywords are ignored. |
        |             |        |                                                           |
        |             |        | **Default**: None                                         |
        +-------------+--------+-----------------------------------------------------------+
        | satellite   | *str*  | Name of the satellite to be included in a standard title. |
        |             |        |                                                           |
        |             |        | **Default**: None                                         |
        +-------------+--------+-----------------------------------------------------------+
        | sensor      | *str*  | Name of the sensor to be included in a standart title.    |
        |             |        |                                                           |
        |             |        | **Default**: None                                         |
        +-------------+--------+-----------------------------------------------------------+
        | product     | *str*  | Name of the product to be included in a standard title.   |
        |             |        |                                                           |
        |             |        | **Default**: None                                         |
        +-------------+--------+-----------------------------------------------------------+
        | date        | *str*  | Date to be included in a standard title.                  |
        |             |        |                                                           |
        |             |        | **Default**: None                                         |
        +-------------+--------+-----------------------------------------------------------+
        | start_time  | *str*  | Start time to be included in a standard title.            |
        |             |        |                                                           |
        |             |        | **Default**: None                                         |
        +-------------+--------+-----------------------------------------------------------+
        | end_time    | *str*  | End time to be included in a standard title.              |
        |             |        |                                                           |
        |             |        | **Default**: None                                         |
        +-------------+--------+-----------------------------------------------------------+
        | copyright   | *str*  | Copyright line to be included in a standard title.        |
        |             |        |                                                           |
        |             |        | **Default**: 'NRL-Monterey'                               |
        +-------------+--------+-----------------------------------------------------------+
        | extra_lines | *list* | Any additional lines to be included in a standard title.  |
        |             |        |                                                           |
        |             |        | **Default**: None                                         |
        +-------------+--------+-----------------------------------------------------------+


        '''

        if lines is not None:
            # Reinitialize other keywords to None
            satellite = None
            sensor = None
            product = None
            date = None
            start_time = None
            end_time = None
            copyright = None
            extra_lines = None
            # If passed a string, split into a list of lines
            if isinstance(lines, str):
                lines = lines.splitlines()
            # Parse first line
            line = lines[0]
            parts = line.split()
            satellite = parts[0]
            sensor = parts[1]
            product = parts[2]
            date = parts[3]
            time_range = parts[4]
            copyright = parts[5]
            time_parts = time_range.split('-')
            start_time = time_parts[0]
            try:
                end_time = time_parts[1]
            except IndexError:
                end_time = None
            if len(lines) > 1:
                extra_lines = lines[1:]

        self.satellite = satellite
        self.sensor = sensor
        self.product = product
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.copyright = copyright
        self.extra_lines = extra_lines
        self.tau = tau

    def __repr__(self):
        return "geoimg.{0}(lines=%r)".format(self.__class__.__name__, self.lines)

    def __str__(self):
        return self.to_str()

    def copy(self):
        'Return a copy of the current object as a new object of the same type.'
        return Title(lines=self.lines)

    @property
    def first_line(self):
        '''
        Get the first line of the title constructed from the object's attributes.

        Returns a string of the form:
        >>> self.satellite self.sensor self.product self.time_range self.copyright

        '''
        line_parts = [self.satellite.upper(),
                      self.sensor.upper(),
                      self.product,
                      self.time_range,
                      self.copyright]
        line = ' '.join(line_parts)
        self._first_line = line
        return self._first_line

    @property
    def lines(self):
        '''
        Get the title as an array of lines.

        '''
        self._lines = [self.first_line]
        if self.extra_lines is not None:
            self._lines.extend(self.extra_lines)
        return self._lines

    def to_str(self):
        '''
        Return the title as a string with line breaks between lines.

        '''
        # These don't seem to actually plot with new lines ?!
        title = '\n'.join(self.lines)
        return title

    @property
    def date(self):
        '''
        Get the date of the title.

        '''
        return self._date

    @date.setter
    def date(self, val):
        self._date = val.replace('/', '')
        return self._date

    @property
    def start_time(self):
        '''
        Get the start time of the title.

        '''
        return self._start_time

    @start_time.setter
    def start_time(self, val):
        if val != '*' and val is not None:
            self._start_time = val.replace(':', '')[0:6].zfill(6)
        else:
            self._start_time = val
        return self._start_time

    @property
    def end_time(self):
        '''
        Get the end time of the title.

        '''
        return self._end_time

    @end_time.setter
    def end_time(self, val):
        if val != '*' and val is not None:
            self._end_time = val.replace(':', '')[0:6].zfill(6)
        else:
            self._end_time = val
        return self._end_time

    @property
    def time_range(self):
        '''
        Get the time range of the title.  Is in the form YYYY/MM/DD HH:MM:SS[-HH:MM:SS]Z.
        The end time is only included if the title's end time is not equal to its start time.

        '''

        if self.start_datetime:
            if self.end_datetime:
                if self.start_datetime == self.end_datetime:
                    self._time_range = self.start_datetime.strftime('%Y/%m/%d %H:%M:%S')
                else:
                    self._time_range = self.start_datetime.strftime('%Y/%m/%d %H:%M:%S') + '-' + \
                        self.end_datetime.strftime('%H:%M:%S')
            else:
                self._time_range = self.start_datetime.strftime('%Y/%m/%d %H:%M:%S')
        else:
            self._time_range = self.end_datetime.strftime('%Y/%m/%d %H:%M:%S')

        self._time_range += 'Z'

        if self.tau:
            self._time_range += ' +{0}H'.format(self.tau)

        return self._time_range

    @property
    def start_datetime(self):
        '''
        Get the start time of the title as a datetime object.

        '''
        if self.start_time != '*' and self.start_time is not None:
            self._start_datetime = datetime.strptime(self.date + self.start_time, '%Y%m%d%H%M%S')
        else:
            self._start_datetime = None
        return self._start_datetime

    @property
    def end_datetime(self):
        '''
        Get the end time of the title as a datetime object.

        '''
        if self.end_time != '*' and self.end_time is not None:
            self._end_datetime = datetime.strptime(self.date + self.end_time, '%Y%m%d%H%M%S')
            try:
                if self._end_datetime < self.start_datetime:
                    self._end_datetime += timedelta(days=1)
            except TypeError:
                pass
        else:
            self._end_datetime = None
        return self._end_datetime

    def combine(self, other):
        '''
        Combine two titles to expand the title's timestamp so that it covers
        the full time range of both titles.

        +------------+---------+------------------------------------------+
        | Parameter: | Type:   | Description:                             |
        +============+=========+==========================================+
        | other      | *Title* | Title to combine with the current title. |
        +------------+---------+------------------------------------------+

        '''
        # Reset the start time if the other file starts earlier
        new_title = self.copy()
        if self.start_datetime > other.start_datetime:
            new_title.date = other.date
            new_title.start_time = other.start_time
        else:
            pass
        # Reset the end time if the other file ends later
        if self.end_datetime < other.end_datetime:
            new_title.end_time = other.end_time
        return new_title

    @staticmethod
    def from_filename(filename, extra_lines=None):
        '''
        Creates a title line given an input utils.path.ProductFileName object.

        '''
        # Unsure what needs to be done with this.  Just a workaround for now...  Ask Mindy what to do.
        if hasattr(filename, 'tau'):
            tau = filename.tau
        else:
            tau = None
        if filename.datetime:
            currdate = filename.datetime.strftime('%Y%m%d')
            currtime = filename.datetime.strftime('%H%M%S')
        else:
            currdate = filename.date
            currtime = filename.time
        return Title(satellite=filename.satname, sensor=filename.sensorname, product=filename.productname,
                     date=currdate, start_time=currtime, end_time=currtime, tau=tau, extra_lines=extra_lines)

    @staticmethod
    def from_objects(datafile, sector, product, extra_lines=None):
        '''
        Creates a title line given an input utils.path.ProductFileName object.

        '''
        # Unsure what needs to be done with this.  Just a workaround for now...  Ask Mindy what to do.
        tau = None
        currdate = datafile.start_datetime.strftime('%Y%m%d')
        currtime = datafile.start_datetime.strftime('%H%M%S')

        # Default to display names in datafile
        sourcename = datafile.source_name_display
        platformname = datafile.platform_name_display

        # If display names in sectorfile doesn't match, use those
        sect_sourcename = sector.sources.sources_dict[datafile.source_name]['source_name_display']
        sect_platformname = sector.sources.sources_dict[datafile.source_name]['platform_name_display']

        if sect_sourcename != sourcename:
            sourcename = sect_sourcename
        if sect_platformname != platformname:
            platformname = sect_platformname

        return Title(satellite=platformname, sensor=sourcename,
                     product=product.product_name_display, date=currdate, start_time=currtime,
                     end_time=currtime, tau=tau, extra_lines=extra_lines)
