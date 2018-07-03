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
import logging
from functools import partial
import time
from functools import wraps
#import warnings
import errno
import os
import signal


# Installed Libraries
from IPython import embed as shell

try:
    errmsg = os.strerror(errno.ETIME)
except AttributeError:
    errmsg = 'Timer ran out'

# GeoIPS Libraries


log=logging.getLogger(__name__)

#class deprecated(object):
#    warnings.simplefilter('always', DeprecationWarning)
#    '''Decorator that can be used to mark functions as deprecated.
#    It will result in a warning being emmitted when the function is used'''
#    def __init__(self, version_number):
#        self.version_number = version_number if version_number else "'Unknown'"
#    def __call__(self, func):
#        def newFunc(*args, **kwargs):
#            warnings.warn(
#                    'Call to deprecated function `%s`.  Deprecated as of version %s and will be removed from future versions.'
#                    % (func.__name__, self.version_number),
#                    category=DeprecationWarning, stacklevel=2,
#                   )
#            return func(*args, **kwargs)
#        newFunc.__name__ = func.__name__
#        newFunc.__doc__ = '''DEPRECATED AS OF VERSION %s\n%s''' % (self.version_number, func.__doc__)
#
#        newFunc.__dict__.update(func.__dict__)
#        return newFunc

class memoized(object):
   """Decorator that caches a function's return value each time it is called.
   If called later with the same arguments, the cached value is returned, and
   not re-evaluated.
   """
   def __init__(self, func):
      self.func = func
      self.cache = {}
   def __call__(self, *args):
      try:
         return self.cache[args]
      except KeyError:
         value = self.func(*args)
         self.cache[args] = value
         return value
      except TypeError:
         # uncachable -- for instance, passing a list as an argument.
         # Better to not cache than to blow up entirely.
         return self.func(*args)
   def __repr__(self):
      """Return the function's docstring."""
      return self.func.__doc__
   def __get__(self, obj, objtype):
      """Support instance methods."""
      return partial(self.__call__, obj)


class TimeoutError(Exception):
    pass

def timeout(seconds=10, error_message=errmsg):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator

def retry(Exception, tries=3, delay=3, backoff=1, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        excpetions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            try_one_last_time = True
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                    try_one_last_time = False
                    break
                except Exception, e:
                    msg = "RETRYING in %d seconds...: MESG: %s" % (mdelay,str(e))
                    log.warning(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            if try_one_last_time:
                return f(*args, **kwargs)
            return
        return f_retry  # true decorator
    return deco_retry

class DocInherit(object):
    """
    Docstring inheriting method descriptor

    The class itself is also used as a decorator

    Usage:
    
    class Foo(object):
        def foo(self):
            "Frobber"
            pass
    
    class Bar(Foo):
        @doc_inherit
        def foo(self):
            pass 
    
    Now, Bar.foo.__doc__ == Bar().foo.__doc__ == Foo.foo.__doc__ == "Frobber"

    """

    def __init__(self, mthd):
        self.mthd = mthd
        self.name = mthd.__name__

    def __get__(self, obj, cls):
        if obj:
            return self.get_with_inst(obj, cls)
        else:
            return self.get_no_inst(cls)

    def get_with_inst(self, obj, cls):

        overridden = getattr(super(cls, obj), self.name, None)
        print 'get_with_inst'
        shell()

        @wraps(self.mthd, assigned=('__name__','__module__'))
        def f(*args, **kwargs):
            return self.mthd(obj, *args, **kwargs)

        return self.use_parent_doc(f, overridden)

    def get_no_inst(self, cls):

        for parent in cls.__mro__[1:]:
            overridden = getattr(parent, self.name, None)
            if overridden: break
        print 'get_no_inst'
        shell()

        @wraps(self.mthd, assigned=('__name__','__module__'))
        def f(*args, **kwargs):
            return self.mthd(*args, **kwargs)

        return self.use_parent_doc(f, overridden)

    def use_parent_doc(self, func, source):
        if source is None:
            raise NameError, ("Can't find '%s' in parents"%self.name)
        func.__doc__ = source.__doc__
        return func

doc_inherit = DocInherit

def doc_set(obj, extend=None):
    '''
    Docstring setting decorator.
    Sets the docstring of the decorated descriptor to the docstring of the
    method of the same name in the passed object.
    If extend is supplied as a string, the contained text will be added to the
    docstring on a new line.
    '''
    def wrap(func):
        try:
            func.__doc__ = getattr(getattr(obj, func.__name__), '__doc__')
        except AttributeError:
            pass
        if extend is not None:
            func.__doc__ += '\n\n'+extend
        return func
    return wrap

#    def __init__(self, mthd):#, omthd):
#        self.mthd = mthd
#        self.name = mthd.__name__
#        shell()
#
#    def __call__(self, omthd):
#        print omthd.__doc__
#        self.omthd = omthd
#
#    def __get__(self, obj, cls):
#        print 'In __get__'
#        #@wraps(self.mthd, assigned=('__name__', '__module__'))
#        #def f(*args, **kwargs):
#        #    return self.mthd(obj, *args, **kwargs)
#        shell()
#        #f.__doc__ = self.omthd.__doc__
#        return self.mthd
#doc_set = DocSet

