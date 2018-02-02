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


# Standard Python Libraries
import os
import logging
import smtplib
from email.mime.text import MIMEText


# Installed Libraries


# GeoIPS Libraries
from .log_setup import interactive_log_setup


log = interactive_log_setup(logging.getLogger('__name__'))


def email_error(errmsg,subject,errorlevel):

    log.error('email_error level: '+str(errorlevel)+' subject: '+str(subject)+' errmsg: '+str(errmsg))
    if not os.getenv('ERROREMAILSTO'):
        log.info('Environment variable ERROREMAILSTO not set, not actually emailing errors. Set environment variables if you would like to receive email notifications of errors.')
        return

    tolist = os.getenv('ERROREMAILSTO').split(',')
    if errorlevel > 1 and os.getenv('ERROREMAILSLEVEL2'):
        tolist = os.getenv('ERROREMAILSLEVEL2').split(',')
    errmsg += ' ****Emailing level '+str(errorlevel)+' support team: '+str(tolist)+'\n'
    log.error(errmsg)

    msg = MIMEText(errmsg)
    msg['Subject'] = subject
    msg['From'] = os.getenv('ERROREMAILSFROM')

    s = smtplib.SMTP('localhost')
    s.sendmail(os.getenv('ERROREMAILSFROM'),tolist,msg.as_string())
    s.quit()
