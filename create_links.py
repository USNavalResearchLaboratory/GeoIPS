#!/bin/env python

# Author:
#    Naval Research Laboratory, Marine Meteorology Division
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the NRLMMD License included with this program.  If you did not
# receive the license, see http://www.nrlmry.navy.mil/geoips for more
# information.

# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# included license for more details.


import os
import commands
import sys

print 'REMEMBER ONLY LINKS FILES THAT ARE IN GIT!!!!'

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

# Setting destinations and plugins appropriately based on environment vars
if os.getenv('STANDALONE_GEOIPS') and os.getenv('STANDALONE_GEOIPS') != os.getenv('GEOIPS'):
    print 'STANDALONE_GEOIPS '+os.getenv('STANDALONE_GEOIPS')
    destinations = [os.getenv('STANDALONE_GEOIPS'),
                    os.getenv('GEOIPS')]
    pluginbases = [os.getenv('STANDALONE_GEOIPS'), os.getenv('GEOIPS')]
else:
    destinations = [os.getenv('GEOIPS')]
    pluginbases = []

print ''


pluginbases += [xx for xx in os.getenv('EXTERNAL_GEOIPS').split(':')]

# Explicitly specifying the geoips subdirectories to link (not including
# sectorfiles and productfiles - those locations are explicitly referenced
# relative to environment variables).
linkedsubdirs = ['/geoips/geoimg', '/geoips/sectorfiles/sectorfiles.dtd',
                 '/geoips/productfiles/productfiles.dtd',
                 '/geoips/pass_prediction', '/geoips/utils',
                 '/geoips/scifile', '/geoips/geoalgs', '/geoips/downloaders',
                 '/geoips/Makefile', '/geoips/driver.py',
                 '/geoips/process_overpass.py', '/geoips/about.py']
# Link the about from each plugin package
for pluginbase in pluginbases:
    linkedsubdirs += ['/geoips/about_'+os.path.split(pluginbase)[-1]+'.py']

print 'pluginbases: '
print pluginbases
print ''
print 'destinations: '
print destinations
print ''

dryrun = False
writegitignore = True
hardlinks = False
# Grab passed arguments
if len(sys.argv) > 1 and sys.argv[1] == 'dryrun':
    dryrun = True
if len(sys.argv) > 1 and sys.argv[1] == 'dontwritegitignore':
    writegitignore = False
if len(sys.argv) > 1 and sys.argv[1] == 'hardlinks':
    # Needed for pip install tarball
    hardlinks = True

print 'pluginbases: '
print pluginbases
print ''
print 'destinations: '
print destinations
print ''
print 'hardlinks: '
print hardlinks
print ''

# Loop through all the destinations that need links (specified based on environment above)
for destbase in destinations:
    # Write gitignore based on links and gitignore file in repo if requested.
    # Force user to delete themselves before running if it already exists.
    if writegitignore:
        gitignore_fname = destbase+'/.gitignore'
        if os.path.exists(gitignore_fname):
            print gitignore_fname+' exists! Delete it if you want a new one.'
            continue
        fileobj = open(gitignore_fname,'w')
        # Add base gitignore information from all locations
        for currdirname in pluginbases+[destbase]:
            if os.path.exists(currdirname+'/gitignore'):
                fileobj.write('# Adding gitignore from '+currdirname+'/gitignore\n')
                for line in open(currdirname+'/gitignore'):
                    fileobj.write(line.strip()+'\n')
    else:
        print('# Adding gitignore from '+destbase+'/gitignore\n')

    # Link all files in each subdirectory specified above
    for linkedsubdir in linkedsubdirs:

        if writegitignore:
            fileobj.write('\n\n\n\n######### Checking subdir '+linkedsubdir+' #########\n\n')

        # Loop through each plugin directory - files need to be linked from
        # each of these directories into the appropriate location in specified
        # destination directories.
        gitfiles = {}
        for pluginbase in pluginbases:
            if os.path.isdir(pluginbase):
                gitfiles[pluginbase] = commands.getoutput('cd '+pluginbase+'; git ls-files').split('\n')
            else:
                gitfiles[pluginbase] = []
        if os.path.isdir(destbase):
            gitfiles[destbase] = commands.getoutput('cd '+destbase+'; git ls-files').split('\n')


        # Check if a file is in git.  Only link files in git!!  (Incidentally,
        # this means new files must at least be added to git in order for them
        # to link properly. Don't have to actually check in)
        def ingit(fname,pluginbase):
            gitname = fname.replace(pluginbase+'/','')
            if os.path.isfile(fname):
                if gitname not in gitfiles[pluginbase]:
                    if dryrun:
                        print 'DO NOT LINK FILE '+fname+' is not under version control'
                    return False
                else:
                    return True
            elif os.path.isdir(fname):
                for gitfile in gitfiles[pluginbase]:
                    if gitname in gitfile:
                        return True
                if dryrun:
                    print 'DO NOT LINK DIR '+fname+' is not under version control'
                return False
            if dryrun:
                print 'DO NOT LINK '+fname+' is not a regular file or directory'
            return False

        for pluginbase in pluginbases:
            if pluginbase == destbase:
                continue
            if writegitignore:
                fileobj.write('\n\n\n##### Attempting to link files from '+pluginbase+linkedsubdir+' to '+destbase+linkedsubdir+' #####\n\n')
            linkeddirs = []
            linkedfiles = []
            for walks in os.walk(pluginbase):
                # os.walk returns a triple:
                #   ('<PATH>',['<SUBDIR1>','<SUBDIR2>'], ['<FILE1>','<FILE2>'])
                currplugindir = walks[0]
                currpluginsubdirs = walks[1]
                currpluginfiles = walks[2]

                # Don't link anything inside a directory that was aready linked.
                waslinked = False
                for linkeddir in linkeddirs:
                    # This test NEEDS the /, but .gitignore CAN NOT have the /
                    if linkeddir+'/' in currplugindir or currplugindir in linkeddirs:
                        #print 'parent directory already linked, not linking '+currplugindir
                        waslinked = True
                if waslinked:
                    continue
                # Don't link .git dir
                if currplugindir == pluginbase+'/.git' or pluginbase+'/.git/' in currplugindir:
                    continue
                for fname in currpluginfiles:
                    # Going to create .gitignore from all these files that we linked, and
                    # the other .gitignores
                    if '.gitignore' in fname:
                        continue
                    pluginpath = currplugindir+'/'+fname
                    destpath = pluginpath.replace(pluginbase,destbase)
                    if not os.path.exists(destpath):
                        #print 'need to link file '+pluginpath
                        if ingit(pluginpath,pluginbase) and linkedsubdir in pluginpath:
                            if not dryrun:
                                print 'linking {}'.format(pluginpath)
                                if hardlinks:
                                    os.link(pluginpath,destpath)
                                else:
                                    os.symlink(pluginpath,destpath)
                            linkedfiles += [pluginpath]
                for subdir in currpluginsubdirs:
                    plugindir = currplugindir+'/'+subdir
                    destdir = plugindir.replace(pluginbase,destbase)
                    if plugindir == pluginbase+'/.git':
                        continue
                    if not os.path.exists(destdir):
                        #print 'need to link dir '+plugindir
                        if ingit(plugindir,pluginbase) and linkedsubdir in plugindir:
                            if not dryrun:
                                print 'linking {}'.format(plugindir)
                                os.symlink(plugindir,destdir)
                            linkeddirs += [plugindir]
                    elif os.path.exists(destdir):
                        if dryrun:
                            print 'dir already exists, not linking: '+destdir
                        pass

            # Concatenate all .gitignores
            if os.path.exists(pluginbase+'/gitignore'):
                if writegitignore:
                    fileobj.write('# Adding gitignore from '+pluginbase+'/gitignore\n')
                    for line in open(pluginbase+'/gitignore'):
                        fileobj.write(line.strip()+'\n')
                else:
                    print('# Adding gitignore from '+pluginbase+'/gitignore\n')
            if writegitignore:
                fileobj.write('\n# LINKED DIRS TO IGNORE FROM '+pluginbase+'\n')
            else:
                print('\n# LINKED DIRS TO IGNORE FROM '+pluginbase+'\n')
            for line in linkeddirs:
                if writegitignore:
                    fileobj.write(line.replace(pluginbase+'/','*')+'\n')
                else:
                    print(line.replace(pluginbase+'/','*')+'\n')
            if writegitignore:
                fileobj.write('\n# LINKED FILES TO IGNORE FROM '+pluginbase+'\n')
            else:
                print('\n# LINKED FILES TO IGNORE FROM '+pluginbase+'\n')
            for line in linkedfiles:
                if writegitignore:
                    fileobj.write(line.replace(pluginbase+'/','*')+'\n')
                else:
                    print(line.replace(pluginbase+'/','*')+'\n')
            if writegitignore:
                print 'cat '+gitignore_fname

print 'REMEMBER ONLY LINKS FILES THAT ARE IN GIT!!!!'
