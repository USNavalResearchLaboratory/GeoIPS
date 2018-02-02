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


# Python Standard Libraries
import logging
import logging.handlers
import os
import commands
import socket
from datetime import datetime


# Installed Libraries


# GeoIPS Libraries
from .plugin_paths import paths as gpaths


INTERACTIVE = 35

longfmt = logging.Formatter('%(asctime)s %(module)s:%(lineno)d %(levelname)s:\t%(message)s',
                            '%d_%H:%M:%S')
shortfmt = logging.Formatter('%(asctime)s:\t%(message)s',
                            '%d_%H:%M:%S')

base_email_subject = '[PYERR]: b=%s u=%s ' % (socket.gethostname(), os.getenv('USER'))
toemails = []
if os.getenv('ERROREMAILSTO'):
    toemails = os.getenv('ERROREMAILSTO').split(',')
# Turning off error emails altogether, too many
toemails = []
fromemail = ''
if os.getenv('ERROREMAILSFROM'):
    fromemail = os.getenv('ERROREMAILSFROM')



def interactive_log_setup(log):
    logging.addLevelName(INTERACTIVE,'INTERACTIVE')
    setattr(log, 'interactive', lambda *args: log.log(INTERACTIVE, *args))
    setattr(log, 'INTERACTIVE', lambda *args: log.log(INTERACTIVE, *args))
    return log

def add_file_hndlr(log,loglevel=logging.INFO,fname=None,fmt=longfmt):
    if fname == None:
        ts = datetime.utcnow()
        fname = gpaths['LOGDIR']+'/gpint/interactive_log_'+ts.strftime('%Y%m%d.%H%M%S')
    print 'ADDING FILE HANDLER: '+str(loglevel)+' '+fname

    dirname = os.path.dirname(fname)
    if not os.path.exists(dirname):
        try:
            os.makedirs(dirname)
        except OSError:
            if os.path.exists(dirname):
                log.info('I guess someone else created the directory before we had a chance to! Thanks! '+dirname)
            else:
                log.error('Failed creating directory '+dirname)
                raise
        log.info('Created directory '+dirname)
    else:
        log.debug('Directory '+dirname+' already exists, not creating')


    file_hndlr = logging.FileHandler(fname)
    file_hndlr.setFormatter(fmt)
    try:
        file_hndlr.setLevel(loglevel)
    except ValueError:
        print '    Warning: invalid log level, using "INFO" level logging'
        loglevel = logging.INFO
        file_hndlr.setLevel(loglevel)
    log.addHandler(file_hndlr)
    return log,file_hndlr

def add_email_hndlr(log,fmt=longfmt,subject='PYERR'):
    email_hndlr = logging.handlers.SMTPHandler('localhost',
                                                   fromemail,
                                                   toemails,
                                                   base_email_subject+subject
                                                  )
    email_hndlr.setFormatter(fmt)
    email_hndlr.setLevel(logging.ERROR)
    log.addHandler(email_hndlr)
    return log,email_hndlr

def add_strm_hndlr(log,loglevel=logging.INFO,fmt=longfmt):
    print 'ADDING STREAM HANDLER: '+str(loglevel)
    stream_hndlr = logging.StreamHandler()
    stream_hndlr.setFormatter(fmt)
    try:
        stream_hndlr.setLevel(loglevel)
    except ValueError:
        print 'Warning: invalid log level, using "INFO" level logging'
        loglevel = logging.INFO
        stream_hndlr.setLevel(loglevel)
    log.addHandler(stream_hndlr)
    return log,stream_hndlr

def root_log_setup(loglevel=logging.INFO,fname=None,subject='PYERR'):
    #print str(datetime.utcnow())+'IN root_log_setup'

    file_hndlr = None
    stream_hndlr = None
    email_hndlr = None

    log = logging.getLogger()
    
    # Set root loggers level to the most verbose - then it will pass all messages to it's individual handlers
    # Then you can filter out messages in the individual handlers setLevel calls
    log.setLevel(logging.DEBUG)
    log = interactive_log_setup(log)

    # Pass string 'interactive' for interactive mode
    try:
        llstr = loglevel.lower()
    except:
        llstr = None
    if llstr:
        if llstr == 'info':
            loglevel = logging.INFO
        elif llstr == 'debug':
            loglevel = logging.DEBUG
        elif llstr == 'warning':
            loglevel = logging.WARNING
        elif llstr == 'error':
            loglevel = logging.ERROR
        elif llstr == 'interactive':
            loglevel = INTERACTIVE
        if not os.getenv('GEOIPS_OPERATIONAL_USER'):
            log,file_hndlr = add_file_hndlr(log,loglevel=logging.INFO,fmt=shortfmt)

    if fname and not os.getenv('GEOIPS_OPERATIONAL_USER'):
        log,file_hndlr = add_file_hndlr(log,loglevel,fname,longfmt)

    else:
        log,stream_hndlr = add_strm_hndlr(log,loglevel,longfmt)

#    if os.getenv('GEOIPS_OPERATIONAL_USER') or subject == 'process_overpass':
#        log,email_hndlr = add_email_hndlr(log,longfmt,subject)

    return log,file_hndlr,email_hndlr

