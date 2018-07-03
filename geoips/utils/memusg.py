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
from __future__ import print_function
import os
import sys
import atexit
import shlex
from argparse import ArgumentParser
from subprocess import Popen, PIPE
from time import sleep
from datetime import datetime

try:
    import resource
except ImportError:
    print('Failed resource import in memusg.py.')

try:
    import psutil
except ImportError:
    print('Failed psutil import in memusg.py.')

import socket
import logging


# Installed Libraries
from matplotlib import pyplot as plt
from IPython import embed as shell


# GeoIPS Libraries
from geoips.utils.log_setup import interactive_log_setup


log = interactive_log_setup(logging.getLogger(__name__))


def print_mem_usage(logstr='',printmemusg=False):
    try:
        log.info('virtual %: '+str(psutil.virtual_memory().percent)+' on '+str(socket.gethostname())+' '+logstr)
        log.info('swap %:    '+str(psutil.swap_memory().percent)+' on '+str(socket.gethostname())+' '+logstr)
    except:
        pass
    try:
        log.info('highest:   '+str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)+' on '+str(socket.gethostname())+' '+logstr)
    except NameError:
        log.info('resource not defined')
    #if printmemusg:
    #    print_resource_usage(logstr)
    pass

def print_resource_usage(logstr=''):
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        for name, desc in [
               ('ru_utime', 'RESOURCE '+logstr+' User time'),
               ('ru_stime', 'RESOURCE '+logstr+' System time'),
               ('ru_maxrss', 'RESOURCE '+logstr+' Max. Resident Set Size'),
               ('ru_ixrss', 'RESOURCE '+logstr+' Shared Memory Size'),
               ('ru_idrss', 'RESOURCE '+logstr+' Unshared Memory Size'),
               ('ru_isrss', 'RESOURCE '+logstr+' Stack Size'),
               ('ru_inblock', 'RESOURCE '+logstr+' Block inputs'),
               ('ru_oublock', 'RESOURCE '+logstr+' Block outputs'),
               ]:
            log.info('%-25s (%-10s) = %s' % (desc, name, getattr(usage, name)))
    except NameError:
        log.info('resource not defined')

class MemUsg(object):
    def __init__(self):
        #Set up lists for output values
        self.times = []
        self.mems = []

        #Add cleanup function
        atexit.register(self.kill_all)

        #Create figure
        self.fig = plt.figure(figsize=(10,10))
        #Add memory plot to figure
        self.memax = self.fig.add_axes((0.1,0.1,0.8,0.8))

    def call_cmd(self, cmd, outfile=None):
        #Set up stdout/stderr pipe
        if outfile is None:
            outf = PIPE
        else:
            outf = open(outfile, 'w')

        #Call the command
        self.proc = Popen(shlex.split(cmd), stdout=outf, stderr=outf)
        print(self.proc.pid)
        while self.proc.poll() is None:
            #Check the process
            self.psproc = Popen(['ps', '-p', str(self.proc.pid), '-o', '%mem', '-h'], stdout=PIPE, stderr=PIPE)
            stdout, stderr = self.psproc.communicate()
            print(stdout.strip(), end=' ')
            outf.flush()
            outf.write('\n********************\nMemUsg: %s%%\n********************\n\n' % stdout.strip())
            outf.flush()
            sys.stdout.flush()

            #Store new values
            self.times.append(datetime.now())
            self.mems.append(float(stdout))

            #Plot the values
            self.memax.plot(self.times, self.mems)
            plt.draw()

            #Sleep for some time
            sleep(1)

    def write(self, fname):
        if fname is None:
            fname = 'memusg.png'
        self.fig.savefig(fname)

    def kill_all(self):
        if hasattr(self, 'proc') and self.proc.poll() is None:
            self.proc.kill()
        if hasattr(self, 'psproc') and self.psproc.poll() is None:
            self.psproc.kill()

if __name__ == '__main__':
    parser = ArgumentParser('Monitor and plot memory usage for a process.')
    parser.add_argument('-o', '--outfile', action='store', type=str, help='Path to a file where stdout and stderr from `command` will be written.')
    parser.add_argument('-p', '--plotfile', action='store', type=os.path.abspath, help='Path to a file where where the graphs will be drawn.')
    parser.add_argument('command', help='A commandline command to monitor.')
    args = parser.parse_args()
    memusg = MemUsg()
    memusg.call_cmd(args.command, args.outfile)
    memusg.write(args.plotfile)

