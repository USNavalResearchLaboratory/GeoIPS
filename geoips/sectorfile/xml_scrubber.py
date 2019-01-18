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

# 20160811  Mindy  Use hard wired 1 day for deleting empty dirs (will make empty directories stick around longer
#                   for very frequently scrubbed stuff, but better for long term scrubs)

# Python Standard Libraries
import os
import operator
import sys
import socket
from datetime import datetime
import logging 
import fnmatch


# Installed Libraries
from IPython import embed as shell
from matplotlib.colors import ColorConverter,LinearSegmentedColormap
import numpy as np


# GeoIPS Libraries
from .SectorFileError import SFAttributeError
from geoips.utils.xml_utilities import read_xmlfile
from geoips.utils.log_setup import interactive_log_setup


log = interactive_log_setup(logging.getLogger('__name__'))

class XMLFiles(object):
    def __init__(self,xfnames,elementname_list=None):

        self.elementname_list = elementname_list
        self.xfnames = xfnames
        self.timestamps = {}
        self.sourcefiles = {}
        self.xmlfiles = []

        for xfname in self.xfnames:
            self.timestamps = {xfname: datetime.fromtimestamp(os.stat(xfname).st_mtime)}
            xf = XMLFile(xfname,elementname_list)
            self.xmlfiles.append(xf)
            for element_name in xf.element_names():
                self.sourcefiles[element_name] = xfname

    def __repr__(self):
        return "xmlfile.%s(%r)" % (self.__class__.__name__, ' '.join(self.xfnames))

    def __str__(self):
        return "xmlfile.%s(%r)" % (self.__class__.__name__, ' '.join(self.xfnames))

    def __add__(self,other):
        '''Concatenating two sectorfiles together.  Adds other.name to list of 
            sectorfile names in self, and adds all sectors from other to self.'''
        log.debug('        XMLFiles + operator') 
        for (name,file) in other.sourcefiles:
            self.sourcefiles[name] = file
        for name in other.xfnames:
            if name not in self.xfnames:
                log.debug('            adding '+name+' to list of sectorfile names')
                self.xfnames.append(name)
                self.xmlfiles.append(XMLFile(name))
                self.timestamps[name] = other.timestamps[name]
        return self

    def open_elements(self,elementname_list):
        elements = []
        for elementname in elementname_list:
            element = self.open_element(elementname)
            if element != None:
                elements.append(element) 
        if not elements:
            return None
        else:
            return elements

    def check_xmlfile(self):
        allsects = {}
        err = '' 
        for xf in self.xmlfiles:
            xf.check_xmlfile(allsects,err)
            

    def element_names(self):
        '''Returns a list of all sector names in the current object.'''
        names = []
        for xf in self.xmlfiles:
            names.extend(xf.element_names())
        return names

    def getelements(self):
        '''Returns a list of all sector elements in the current object.'''
        allelts= []
        for xf in self.xmlfiles:
            allelts.extend(xf.getelements())
        return allelts
            
    def iterelements(self):
        '''Iterates over all sector elements in the current object.'''
        ind = 1
        for xf in self.xmlfiles:
            elts = xf.iterelements()
            while True:
                try:
                    yield elts.next()
                except StopIteration:
                    break

    def open_element(self, name):
        '''Instantiates a Sector object by short name.'''
        #try:
        #    element = self.root.xpath('sector[@name="%s"]' % name)[0]
        #except IndexError:
        #    return None
        #return Sector(element, self.date, self.time)
        for xf in self.xmlfiles:
            elt = xf.open_element(name)
            if elt != None:
                return elt
            #If no sector found, return None
        return None
    

class XMLFile(object):
    def __init__(self,xfname,elementname_list=None,force=False):
        self.xfname = xfname
        self.timestamp = datetime.fromtimestamp(os.stat(xfname).st_mtime)
        self.elementname_list = elementname_list
        self.force = force
        if not os.path.isfile(xfname):
            raise IOError('File does not exist: %s' % xfname)
        self.tree = read_xmlfile(xfname, do_objectify=True)
        self.root = self.tree.getroot()

    def element_names(self):
        '''Returns a list of all sector names in the current object.
            Skip things not in self.elementname_list'''
        # Generalize this for any xml file of the
        # <xmltype_list>
        #   <xmltype name="test">
        # format

        # getchildren() gets all of the tags below <xmltype_list>
        #   this would be all of the <xmltype> tags 
        #   (ie, <scrubber> or <colorbar>)
        # elt.tag is the <xmltype>
        #       ie <colorbar name='testcb'>
        #       elt.tag = 'colorbar'
        # elt.items() is a list of tuples of attributes to the tag
        #       ie <colorbar name='testcb' arg='no'>
        #       elt.items() = [('name', 'testcb'), ('arg', 'no')]
        element_names = []
        for elt in self.root.getchildren():
            for attr in elt.items():
                if attr[0] == 'name':
                    element_names += [attr[1]]
        #element_names = self.root.xpath('scrubber/@name')

        allelement_names = []
        for element_name in element_names:
            if self.check_element(element_name) == True:
                allelement_names.append(element_name)
        return allelement_names

    def check_element(self,name):
        if self.elementname_list != None and name.lower() not in [x.lower() for x in self.elementname_list]:
            return False
        return True

    def open_element(self,name,start_dt=None):
        '''Instantiates an Element object by short name.'''
        # Generalize this for any xml file of the
        # <xmltype_list>
        #   <xmltype name="test">
        # format

        # getchildren() gets all of the tags below <xmltype_list>
        #   this would be all of the <xmltype> tags 
        #   (ie, <scrubber> or <colorbar>)
        # elt.tag is the <xmltype>
        #       ie <colorbar name='testcb'>
        #       elt.tag = 'colorbar'
        # elt.items() is a list of tuples of attributes to the tag
        #       ie <colorbar name='testcb' arg='no'>
        #       elt.items() = [('name', 'testcb'), ('arg', 'no')]
        #elements = self.root.xpath('scrubber')
        elements = self.root.getchildren()
        for element in elements:
            # Check the name attribute on the <xmltype> tag, if
            # it matches the name passed to open_element, then 
            # open the class that matches element.tag
            if element.attrib['name'].lower() == name.lower():
                # This will return class like:
                #   sectorfile.xml_scrubber.colorbar
                #   sectorfile.xml_scrubber.scrubber
                # class names should match tag name in xml file
                # ie element.tag = 'colorbar', open sectorfile.xml_scrubber.colorbar class.
                eltclass = getattr(sys.modules[__name__],element.tag)
                #elt = scrubber(element, self.timestamp,self.xfname,self.force,start_dt)
                elt = eltclass(element, self.timestamp,self.xfname,self.force,start_dt)
                if self.check_element(elt.name) == True:
                    return elt
        #If no element found, return None
        return None

class Element(object):
    def __init__(self,element,timestamp=None,sourcefile=None):
        self.node =  element
        self.timestamp=timestamp
        self.sourcefile = sourcefile


class XMLInstance(object):
    '''This is the base instance found in the general XML file. Standard xml files are of the form:
        <xmlinstancetype_list>
            <xmlinstancetype name='xmlinstancetypename'>
        class for specific xmlinstance should be 
        class xmlinstancetype'''
    def get_bool_att(self, name, path='.'):
        val = self.node.xpath('%s/@%s' % (path, name))[0]
        try:
            onoff = str_to_bool(val)
        except ValueError:
            raise SFAttributeError('%s/@%s attribute for %s sector must be either yes or no' 
                                   % (path, name, self.name))
        return onoff
    def set_bool_att(self, name, val, path='.'):
        val = bool_to_str(val)
        elem = self.node.xpath(path)[0]
        elem.set(name, val)

    @property
    def name(self):
        '''Getter method for sector's short name.'''
        self._name = self.node.xpath('@name')[0]
        return self._name
    @name.setter
    def name(self, val):
        '''Setter method for sector's short name.'''
        self.node.set('name', val)

class sector(XMLInstance):
    ''' Specific XML Instance type - xml tags should be named like:
            In xml file:
                <xmlinstancetype_list>
                    <xmlinstancetype name="testname">
            in xml_scrubber.py:
                class xmlinstancetype
            will automatically use class xmlinstancetype for xmlinstancetype tag.
    '''
    def __init__(self,element,timestamp=None,sourcefile=None,force=False,start_dt=None):
        self.node =  element
        self.timestamp=timestamp
        self.sourcefile = sourcefile


class colorbar(XMLInstance):
    ''' Specific XML Instance type - xml tags should be named like:
            In xml file:
                <xmlinstancetype_list>
                    <xmlinstancetype name="testname">
            in xml_scrubber.py:
                class xmlinstancetype
            will automatically use class xmlinstancetype for xmlinstancetype tag.
    '''
    def __init__(self,element,timestamp=None,sourcefile=None,force=False,start_dt=None):
        self.node =  element
        self.timestamp=timestamp
        self.sourcefile = sourcefile

    def create_colorbar(self):
        ''' Use values from xml file to fill in the dict used in LinearSegmentedColormap
            Must normalize to 0 to 1 using min_val and max_val specified in xml.

            TRANSITIONPOINT1 = 0.0
            TRANSITIONPOINT4 = 1.0
            cmdict = { 'red' :  ((TRANSITIONPOINT1, IGNORED, 1to2STARTCOLOR),
                             (TRANSITIONPOINT2, 1to2ENDCOLOR, 2to3STARTCOLOR),
                             (TRANSITIONPOINT3, 2to3ENDCOLOR, 3to4STARTCOLOR),
                             (TRANSITIONPOINT4, 3to4ENDCOLOR, IGNORED)),
                   'green' :  ((TRANSITIONPOINT1, IGNORED, 1to2STARTCOLOR),
                             (TRANSITIONPOINT2, 1to2ENDCOLOR, 2to3STARTCOLOR),
                             (TRANSITIONPOINT3, 2to3ENDCOLOR, 3to4STARTCOLOR),
                             (TRANSITIONPOINT4, 3to4ENDCOLOR, IGNORED)),
                        
                   'blue' :  ((TRANSITIONPOINT1, IGNORED, 1to2STARTCOLOR),
                             (TRANSITIONPOINT2, 1to2ENDCOLOR, 2to3STARTCOLOR),
                             (TRANSITIONPOINT3, 2to3ENDCOLOR, 3to4STARTCOLOR),
                             (TRANSITIONPOINT4, 3to4ENDCOLOR, IGNORED)),
                }
        ''' 
        # Sort transitions on start_val
        transitions = sorted(self.node.xpath('transition'),key=operator.attrgetter('start_val'))
        bluetuple = ()
        greentuple = ()
        redtuple = ()
        start_color = None
        end_color = None
        old_end_color = [0,0,0]
        for transition in transitions:
            # Must start with 0.0 !
            transition_point = (transition.start_val - self.node.min_val) / float((self.node.max_val - self.node.min_val))
            cc = ColorConverter()
            # Convert start/end color to string, tuple, whatever matplotlib can use.
            try:
                start_color = cc.to_rgb(str(transition.start_color))
            except ValueError:
                # Allow for tuples as well as string representations
                start_color = cc.to_rgb(eval(str(transition.start_color)))
            try:
                end_color = cc.to_rgb(str(transition.end_color))
            except ValueError:
                end_color = cc.to_rgb(eval(str(transition.end_color)))
            bluetuple += ((transition_point,old_end_color[2],start_color[2]),)
            redtuple += ((transition_point,old_end_color[0],start_color[0]),)
            greentuple += ((transition_point,old_end_color[1],start_color[1]),)
            log.info('    Transition point: '+str(transition_point)+': '+str(transition.start_val)+' to '+str(transition.end_val))
            log.info('        Start color: %-10s %-40s'%(str(transition.start_color),str(start_color)))
            log.info('        End color:   %-10s %-40s'%(str(transition.end_color),str(end_color)))
            old_end_color = end_color
        # Must finish with 1.0 !
        transition_point = (transition.end_val - self.node.min_val) / float((self.node.max_val - self.node.min_val))
        bluetuple += ((transition_point,old_end_color[2],start_color[2]),)
        redtuple += ((transition_point,old_end_color[0],start_color[0]),)
        greentuple += ((transition_point,old_end_color[1],start_color[1]),)

        cmdict = { 'red': redtuple,
                   'green': greentuple,
                   'blue': bluetuple
                 }
        cm = LinearSegmentedColormap(self.name,cmdict)
        ascii_cm = LinearSegmentedColormap.__call__(cm,np.arange(256))

        return ascii_cm

    def write_colorbar(self,fname=None):

        cm = self.create_colorbar()[:,0:3]

        if not fname:
            cbpath = os.getenv('GEOIPS')+'/geoips/geoimg/test_palettes/'+self.name
        else:
            cbpath = fname
            if os.path.exists(cbpath):
                print('Cowardly refusing to overwrite existing colorbar file '+cbpath+' . Delete it yourself if you want to recreate.')
                return False


        if not os.path.exists(os.path.dirname(cbpath)):
            os.makedirs(os.path.dirname(cbpath))
        cbfile = open(cbpath,'w')

        log.info('Writing colorbar '+self.name+' to file '+cbpath)

        for rgb in cm:
            cbfile.write(' '.join(str(pc) for pc in rgb)+'\n')
            #print(' '.join(str(pc) for pc in rgb))

        return True

class scrubber(XMLInstance):
    def __init__(self,element,timestamp=None,sourcefile=None,force=False,start_dt = None):
        self.node =  element
        self.timestamp=timestamp
        self.sourcefile = sourcefile
        self.runonboxes = self.node.xpath('box')
        self.runasusers = self.node.xpath('user')
        self.currentbox = socket.gethostname()
        self.currentuser = os.getenv('USER')
        self.paths = self.node.xpath('path')
        self.force = force
        try:
            self.num_minutes = self.node.num_minutes
        except AttributeError:
            self.num_minutes = ''
        try:
            self.num_days = self.node.num_days
        except AttributeError:
            self.num_days = ''
        if start_dt:
            self.start_dt = start_dt
        else:
            self.start_dt = datetime.utcnow()
        self.ignore_dirs = self.node.xpath('ignore_dir')
        self.run_hours = self.node.xpath('run_hour')
        self.run_days_of_week = self.node.xpath('run_day_of_week')


    @property
    def recursive(self):
        '''Getter method for recursive flag.'''
        self._recursive = self.get_bool_att('recursive')
        return self._recursive
    @recursive.setter
    def recursive(self, val):
        '''Setter method for recursive flag.'''
        self.set_bool_att('recursive',val)

    @property
    def isactive(self):
        '''Getter method for active flag.'''
        self._isactive= self.get_bool_att('active')
        return self._isactive
    @isactive.setter
    def isactive(self, val):
        '''Setter method for active flag.'''
        self.set_bool_att('active',val)

#find . \( -path './masters' -o -path './sectorfiles' \) -prune -o -mtime +10 -print -exec rm -f {} \;
#find . -type d \( -path './masters' -o -path './sectorfiles' \) -prune -o -empty -print -exec rmdir {} \;

    @property
    def delete_empty_dirs(self):
        '''Getter method for sector's short name.'''
        self._delete_empty_dirs = self.get_bool_att('delete_empty_dirs')
        return self._delete_empty_dirs
    @delete_empty_dirs.setter
    def delete_empty_dirs(self, val):
        '''Setter method for sector's short name.'''
        self.set_bool_att('delete_empty_dirs', val)

    def scrub(self):
        asterisks = '*'*40
        log.info('\n\n\n\n\nCurrent box: '+self.currentbox)

        retval = False

        file_age_string = ''
        dir_age_string = ''

        if self.num_minutes and self.num_days:
            log.error('Can not define num_minutes and num_days - fix xml file')
            return None
        elif self.num_minutes:
            if not str(self.num_minutes).isdigit():
                log.warning('NUM_MINUTES IS NOT AN INTEGER!!! NOT ACTUALLY RUNNING!!!!')
                return None
            file_age_string = '-mmin +'+str(self.num_minutes) 
            #MLS 20160811 dir_age_string no longer used for now (hard code 1 day for empty directories)
            dir_age_string = '-cmin +'+str(self.num_minutes) 
        elif self.num_days:
            if not str(self.num_days).isdigit():
                log.warning('NUM_DAYS IS NOT AN INTEGER!!! NOT ACTUALLY RUNNING!!!!')
                return None
            file_age_string = '-mtime +'+str(self.num_days)
            #MLS 20160811 dir_age_string no longer used for now (hard code 1 day for empty directories)
            dir_age_string = '-ctime +'+str(self.num_days)
        else:
            log.error('Must define either num_days or num_minutes, fix xml file')
            return None
            

        run_hours_string = 'every hour'
        if self.run_hours:
            run_hours_string = 'hours '+' and '.join([str(xx) for xx in self.run_hours])

        days_of_week_string = 'every day'
        if self.run_days_of_week:
            days_of_week_string = 'every '+' and '.join([str(xx) for xx in self.run_days_of_week])

        log.info('\n'+asterisks+'Starting next scrub '+self.name+asterisks+' on box '+self.currentbox+'\n'+
                asterisks+'Scrubbing on '+run_hours_string+' of '+days_of_week_string+asterisks+'\n')

        # MLS 20151214 Took runonboxes out - still can list boxes in scrub sectorfile, but it doesn't actually 
        #     do anything. Eventually, implement ability to limit to specific boxes IF any are listed
        #     (if no boxes listed, just run on any box)
        #log.info([self.currentbox])
        #log.info([runonbox for runonbox in self.runonboxes])
        #log.info(self.runonboxes)
        #log.info(fnmatch.filter([self.currentbox],'kauai*'))
        #log.info(fnmatch.filter([self.currentbox],runonbox) for runonbox in self.runonboxes)
        #shell()

        #if True in [fnmatch.filter([self.currentbox],runonbox) for runonbox in self.runonboxes]:
        #    log.warning('NOT ACTUALLY RUNNING: current box '+self.currentbox+' is not in run on boxes '+str(self.runonboxes))
        #    log.info(asterisks)
        #    return None
        if self.currentuser not in self.runasusers:
            log.warning('NOT ACTUALLY RUNNING: current user '+self.currentuser+' is not in run as users '+str(self.runasusers))
            log.info(asterisks)
            return None


        ########################################################################
        ###  Compiling list of directories to ignore when scrubbing          ###
        ###  We are ignoring *ignore_dir*                                    ###
        ###      Completely skip scrubbing if:                               ###
        ###         Any ignore dir contains a space (that could do bad things### 
        ###             things since it is in the middle of a command line   ### 
        ###             call)                                                ###
        ###         Any ignore dir contains a '$' (that means environment    ###
        ###             variables failed to expand - don't run if we         ###
        ###             don't have all the necessary env vars.               ###
        ########################################################################
        ignore_str=''
        if self.ignore_dirs:
            log.info('Ignoring directories: '+str(self.ignore_dirs))
            good_ignore_dirs = []
            for xx in self.ignore_dirs:
                ignore_dir = os.path.expandvars(str(xx))
                if ' ' in ignore_dir:
                    log.error('IGNORE DIRECTORY INVALID, CANNOT CONTAIN SPACES, NOT ACTUALLY RUNNING '+ignore_dir)
                    return None
                elif '$' in ignore_dir:
                    log.error('IGNORE DIRECTORY CONTAINS A $, os.path.expandvars must have missed a variable, NOT ACTUALLY RUNNING '+ignore_dir)
                    return None
                else:
                    good_ignore_dirs.append(ignore_dir)
            ignore_dirs = ["-path '*"+ignore_dir+"*'" for ignore_dir in good_ignore_dirs]
            ignore_str='\( '+' -o '.join(ignore_dirs)+' \) -prune -o '

        ########################################################################
        ### Running through all paths listed for current scrubber in xml file###
        ### Compiling the find command that handles the delete of files      ###
        ###     individually (no -r)                                         ###
        ### Will skip current path if: ###
        ###     currpath does not exist                                      ###
        ###     len of currpath str is < 3 (can't accidentally scrub /)      ###
        ###     $ in currpath (means environment variable did not expand)    ###
        ########################################################################
        for currpath in self.paths:
            currpath = os.path.expandvars(str(currpath))
            deletefilescall = '/usr/bin/find '+currpath+' '+ignore_str+' -user '+self.currentuser+' -type f '+file_age_string+' -print0 | xargs -0 rm -vf ' 
            log.info('\n\nRunning find command on \''+self.name+'\'...'+
                     '\n'+asterisks+'FILES'+asterisks+'\n'+deletefilescall+'\n'+asterisks+'FILES'+asterisks) 
            log.info('Current day of week: '+self.start_dt.strftime('%A'))
            log.info('Current hour of day: '+str(int(self.start_dt.strftime('%H'))))
            log.info('self.isactive: '+str(self.isactive))
            if not self.isactive:
                log.warning('Scrubber is set as inactive, not actually running!!!!')
            elif not os.path.exists(str(currpath)):
                log.warning('FIND PATH DOES NOT EXIST!!! NOT ACTUALLY RUNNING!!!!')
            elif len(str(currpath)) < 3:
                log.warning('FIND PATH LENGTH IS LESS THAN 3!!! That is not a good idea.')
            elif '$' in str(currpath):
                log.warning('FIND PATH CONTAINS A $. PARANOIA PREVENTS ME FROM SCRUBBING (an environment variable was not expanded)')
            else:
                if (self.force == True or ((not self.run_days_of_week or self.start_dt.strftime('%A') in [str(xx) for xx in self.run_days_of_week]) and
                    (not self.run_hours or int(self.start_dt.strftime('%H')) in [int(str(xx)) for xx in self.run_hours]))):
                    #deletefilescall = '/usr/bin/find '+currpath+' '+ignore_str+' -type f -mtime +'+str(self.num_days)+' -print -exec rm -f {} \;' 
                    if self.force == True:
                        log.info('Force was set to True, running even if hour doesn\'t match')
                    log.info('Running scrubber '+self.name+' ...')
                    os.system(deletefilescall) 
                    retval = True
                    # MLS 20160328  Need to fix this to set dir_age_string to like 1 day. Don't want to 
                    #               delete all empty dirs (could delete brand new one before file placed 
                    #               in it), but should wait until it is as old as the files we deleted.
                    # MLS 20160811  Hard code ctime 1 for empty directories.
                    if self.delete_empty_dirs:
                        if not os.path.exists(str(currpath)):
                            log.warning('FIND PATH DOES NOT EXIST!!! NOT ACTUALLY DELETING DIRECTORIES!!!!')
                        else:
                            #deletedirscall = '/usr/bin/find '+currpath+' '+ignore_str+' -empty -type d -print -exec rmdir {} \;'
                            #deletedirscall = '/usr/bin/find '+currpath+' '+ignore_str+' -user '+self.currentuser+' -type d -empty '+dir_age_string+' -print0 | xargs -0 rmdir -v'
                            deletedirscall = '/usr/bin/find '+currpath+' '+ignore_str+' -user '+self.currentuser+' -type d -empty -ctime +1 -print0 | xargs -0 rmdir -v'
                            log.info('\n\nRunning find delete dirs command on \''+self.name+'\'...'+
                                    '\n'+asterisks+'DIRS'+asterisks+'\n'+deletedirscall+'\n'+asterisks+'DIR'+asterisks) 
                            os.system(deletedirscall) 
                else:
                    if self.run_days_of_week:
                        log.info('SKIPPING Only running \''+self.name+'\' at day of week = '+str(self.run_days_of_week))
                    if self.run_hours:
                        log.info('SKIPPING Only running \''+self.name+'\' at UTC hour = '+str(self.run_hours))
        log.info('\n'+asterisks+'Ending scrub'+asterisks)
        return retval

def str_to_bool(val, yes='yes', no='no'):
    '''Converts a "boolean" string to a boolean.
    If val equals the value of yes, then return True.
    If val equals the value of no, then return False.
    If val equals neither the value of yes or no, raise a ValueError.
    Arguments:
        val - String to convert to boolean
    Keywords:
        yes - Value to use as True
        no  - Value to use as False
    '''
    #If val is already a boolean return it now
    if val is True or val is False:
        return val
    #Test val and return appropriate boolean
    if val.lower() == yes.lower():
        return True
    elif val.lower() == no.lower():
        return False
    else:
        raise ValueError('Value must be str(%s) or str(%s).  Got %r.' % (yes, no, val))

def bool_to_str(val, yes='yes', no='no'):
    '''Converts a boolean to a "boolean" string.
    If val is True then return the value of yes.
    If val is False then return the value of no.
    If val is neither True nor False then raise a ValueError.
    Arguments:
        val - A boolean
    Keywords:
        yes - Value to use as True
        no  - Value to use as False
    '''
    #If val already equals either yes or no return it now
    if val == yes or val == no:
        return val
    if val is True:
        return yes
    elif val is False:
        return no
    else:
        raise ValueError('Value must be True or False.  Got %r.' % (yes, no, val)) 
