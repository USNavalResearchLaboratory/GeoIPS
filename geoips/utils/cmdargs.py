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
from copy import copy


# Installed Libraries


# GeoIPS Libraries


class ArgumentError(Exception):
    pass

class CMDArgs(object):
    def __init__(self, *positionals, **options):
        '''THIS NEEDS TO BE DOCUMENTED!!!'''
        #Initialize positional arguments list
        self._positionals = []
        for arg in positionals:
            self.addarg(arg)

        #Initialize options dictionary
        self._options = {}
        for (opt, val) in options.items():
            self.addopt(opt, val)

    def __repr__(self):
        return '%s(positionals=%s, options=%s)' % (self.__class__.__name__, self._positionals, self._options)

    def __str__(self):
        pos = ' '.join(self._positionals)
        opt = ' '.join(['%s %s' % self._make_opt_str(opt, val) for (opt, val) in self._options.items()])
        return '%s %s' % (pos, opt)

    @property
    def positionals(self):
        '''Return the list of positional arguments.'''
        return self._positionals

    @property
    def options(self):
        '''Return dictionary of option, value pairs.'''
        return self._options

    def addarg(self, arg):
        '''Add a positional argument to the list of arguments.'''
        self._positionals.append(arg)

    def delarg(self, index):
        '''Delete an argument from the constructor by index.'''
        self._positionals.pop(index)

    def addopt(self, opt, *vals):
        '''Add an option the constrcutor.'''
        self._options[opt] = vals
        #if val is not None:
        #    self._options[opt] = val
        #else:
        #    #Use an empty string rather than None here since this will be joined together into a command
        #    self._options[opt] = ''

    def delopt(self, opt):
        '''Delete an option fromt the constructor by name.'''
        try:
            self._options.pop(opt)
        except KeyError:
            raise ArgumentError('No such option: %s' % opt)

    def _get_optstr(self, opt):
        '''Prepends a single dash if `arg` is one character long
        and a double dash if `arg` is more than one character long.
        '''
        if len(opt) == 1:
            opt = '-'+opt
        else:
            opt = '--'+opt
        return opt

    def get_arglist(self):
        args = copy(self._positionals)
        args.extend(['%s %s' % self._make_opt_str(opt, val) for (opt, val) in self._options.items()])
        return args

    def _make_opt_str(self, opt, vals):
        '''Turn an option's name into an option with dashes
        and an options's value(s) into a single string.'''
        opt = self._get_optstr(opt)
        val = ' '.join([str(val) for val in vals]).strip()
        if val:
            val = "'"+val+"'"
        return opt, val
