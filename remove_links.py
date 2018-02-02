#!/bin/env

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

import os
import sys
try:
    from IPython import embed as shell
except:
    print 'Failed IPython import in remove_links.py. If you need it, install it.'

# Nothing to delete if GEOIPS and EXTERNAL_GEOIPS are not defined. Exit.
if not os.getenv('GEOIPS'):
    print 'Must define $GEOIPS in environment.  Failing.'
    sys.exit()
else:
    print 'GEOIPS ' + os.getenv('GEOIPS')

if not os.getenv('EXTERNAL_GEOIPS'):
    print 'EXTERNAL_GEOIPS not defined, no plugins to link. Exiting.'
    sys.exit()
else:
    print 'EXTERNAL_GEOIPS ' + \
            os.getenv('EXTERNAL_GEOIPS')

# Will delete all links in STANDALONE_GEOIPS and GEOIPS
if os.getenv('STANDALONE_GEOIPS'):
    print 'STANDALONE_GEOIPS '+os.getenv('STANDALONE_GEOIPS')
    destinations = [os.getenv('STANDALONE_GEOIPS'),
                    os.getenv('GEOIPS')]
else:
    destinations = [os.getenv('GEOIPS')]

# Must pass 'all' to delete links that are not listed in .gitignore.
dryrun = False
runall = False
if len(sys.argv) > 1 and sys.argv[1] == 'all':
    runall = True
if len(sys.argv) > 2 and sys.argv[2] == 'dryrun':
    dryrun = True

for destbase in destinations:

    # Just delete all links (except in geoalgs/lib, so we don't have to rebuild)
    if runall:
        if not dryrun and os.path.exists(destbase+'/.gitignore'):
            print 'Removing .gitignore: '+destbase+'/.gitignore'
            os.unlink(destbase+'/.gitignore')
        for walk in os.walk(destbase):
            if '/.git/' not in walk[0] and '/geoalgs/lib' not in walk[0]:
                for fname in walk[2]:
                    if os.path.islink(walk[0]+'/'+fname):
                        print 'Removing file link: '+walk[0]+'/'+fname
                        if not dryrun:
                            os.unlink(walk[0]+'/'+fname)
                for dirname in walk[1]:
                    if os.path.islink(walk[0]+'/'+dirname):
                        print 'Removing directory link: '+walk[0]+'/'+dirname
                        if not dryrun:
                            os.unlink(walk[0]+'/'+dirname)

    # Only delete links in .gitignore
    elif not runall:
        startunlinking = False
        #Only remove links found in .gitignore
        gitignorefile = destbase+'/.gitignore'
        if os.path.isfile(gitignorefile):
            for line in open(gitignorefile):
                if '# LINKED FILES TO IGNORE FROM ' in line:
                    startunlinking = True
                    what = 'FILE'
                if '# LINKED DIRS TO IGNORE FROM ' in line:
                    startunlinking = True
                    what = 'DIR'
                if startunlinking:
                    linkfile = line.strip().replace('*',destbase+'/')
                    if os.path.islink(linkfile):
                        print 'Removing linked '+what+' listed in .gitignore: '+linkfile
                        if not dryrun:
                            os.unlink(linkfile)
        else:
            print 'gitignore file does not exist, not deleting any links: '+gitignorefile
