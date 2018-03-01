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
import time
import commands
import os
import logging
import argparse
from socket import gethostname
from subprocess import Popen, PIPE
import textwrap
import shlex


# Installed Libraries
from IPython import embed as shell


# GeoIPS Libraries
from geoips.utils.log_setup import root_log_setup,interactive_log_setup
from geoips.utils.cmdargs import CMDArgs
from geoips.utils.plugin_paths import paths as gpaths


log = interactive_log_setup(logging.getLogger(__name__))

def wait_for_queue(sleeptime = 30,
                   give_up_time=None,
                   queue='batch@kahuna',
                   job_limits_Ronly={'GD':5},
                   job_limits_RandQ={'GW':35},
                   max_total_jobs=500,
                   max_user_jobs=10,
                   current_sleep_time=0,
                   have_max_running=False):
    '''
    Check the status of a PBS queue and wait for specific conditions to be met
    prior to continuing execution.

    :docnote:`I really like this function. I think it should be packaged more generically in`
    :docnote:`a PBS package that includes this, qsub, and any other scripts that we`
    :docnote:`develop in the future for interfacing with PBS queues.`

    +--------------------+--------+-----------------------------------------------------------------+
    | Keyword:           | Type:  | Description:                                                    |
    +====================+========+=================================================================+
    | sleeptime          | *int*  | Number of seconds to wait between checking the queue.           |
    |                    |        |                                                                 |
    |                    |        | **Default:** 30                                                 |
    +--------------------+--------+-----------------------------------------------------------------+
    | give_up_time       | *int*  | Number of seconds to allow before giving up entirely.           |
    |                    |        |                                                                 |
    |                    |        | Raises :class:DownloaderGiveup                                  |
    |                    |        |                                                                 |
    |                    |        | **Default:** None                                               |
    +--------------------+--------+-----------------------------------------------------------------+
    | current_sleep_time | *int*  | The total amount of time we have slept so far (as wait_for_queue|
    |                    |        | is called recursively, we pass this incremented value in with   |
    |                    |        | each call).                                                     |
    |                    |        |                                                                 |
    |                    |        | **Default:** 0                                                  |
    +--------------------+--------+-----------------------------------------------------------------+
    | queue              | *str*  | Name of the queue to check of the form queuename[@hostname].    |
    |                    |        | If the queue is on the local host, only the queue's name is     |
    |                    |        | required, but the hostname must be provided if the queue is on  |
    |                    |        | a remote host.                                                  |
    |                    |        |                                                                 |
    |                    |        | **Default:** 'batch@kahuna'                                     |
    +--------------------+--------+-----------------------------------------------------------------+
    | job_limits_Ronly   | *dict* | Names of jobs to look for in the queue, and the associated      |
    |                    |        | number allowed at any given time. These will be counted         |
    |                    |        | and used to determine whether or not we are under our           |
    |                    |        | thresholds.                                                     |
    |                    |        |                                                                 |
    |                    |        | This ONLY included Running jobs in the counts. Use              |
    |                    |        | job_limits_RandQ to include running and queued.                 |
    |                    |        |                                                                 |
    |                    |        | Note this simply looks for the given substring within the qstat |
    |                    |        | output.  You can also use wildcards (.*) within the job_limits  |
    |                    |        | keys if needed.                                                 |
    |                    |        |                                                                 |
    |                    |        | **Default:** {'GD':5}                                           |
    +--------------------+--------+-----------------------------------------------------------------+
    | job_limits_RandQ   | *dict* | Names of jobs to look for in the queue, and the associated      |
    |                    |        | number allowed at any given time. These will be counted         |
    |                    |        | and used to determine whether or not we are under our           |
    |                    |        | thresholds.                                                     |
    |                    |        |                                                                 |
    |                    |        | This includes both Running jobs and Queued jobs in the counts.  |
    |                    |        | Use job_limits_RandQ to include only running                    |
    |                    |        |                                                                 |
    |                    |        | Note this simply looks for the given substring within the qstat |
    |                    |        | output.  You can also use wildcards (.*) within the job_limits  |
    |                    |        | keys if needed.                                                 |
    |                    |        |                                                                 |
    |                    |        | **Default:** {'GW':35}                                          |
    +--------------------+--------+-----------------------------------------------------------------+
    | max_user_jobs      | *int*  | Maximum number of total jobs to allow at one time for current   |
    |                    |        | user if NOT operational user (we will not limit operations)     |
    |                    |        | Will contiue to sleep until we are under this many total jobs   |
    |                    |        | for given user in the queue.                                    |
    |                    |        |                                                                 |
    |                    |        | Will die if this contition is not met before ``give_up_time``   |
    |                    |        | seconds have passed.                                            |
    |                    |        |                                                                 |
    |                    |        | **Default:** 100                                                |
    +--------------------+--------+-----------------------------------------------------------------+
    | max_total_jobs     | *int*  | Maximum number of total jobs to allow at one time.              |
    |                    |        | Will contiue to sleep until we are under this many total jobs   |
    |                    |        | in the queue.                                                   |
    |                    |        |                                                                 |
    |                    |        | Will die if this contition is not met before ``give_up_time``   |
    |                    |        | seconds have passed.                                            |
    |                    |        |                                                                 |
    |                    |        | **Default:** 500                                                |
    +--------------------+--------+-----------------------------------------------------------------+

    '''

    if not queue:
        log.info('Not using queue, don\'t have to wait!')
        return True

    # MLS 20160226 FNMOC is specified as just satq, not queue_name@queue_box
    try:
        queue_name,queue_box = queue.split('@') 
    except ValueError:
        queue_name = queue
        queue_box = queue

    # Grep qstat for: qstat | grep "[QR] batch"
    qstat_cmd = 'qstat | grep "[QR] '+queue_name+'"'
    log.info('Checking queue with: '+qstat_cmd)
    jobs = commands.getoutput(qstat_cmd).split('\n')

    # Briefly we were only qsubbing some jobs to the fourinones 
    # (not compute-0-0). Include these jobs.
    qstat_cmd = 'qstat | grep "[QR] fourinone@kahuna"'
    #log.info('Checking queue with: '+qstat_cmd)
    jobs += commands.getoutput(qstat_cmd).split('\n')

    user_num_jobs = 0
    user_num_running = 0
    user_num_queued = 0
    
    # Explicitly limit non-operational jobs to a subset of total jobs available
    if not os.getenv('GEOIPS_OPERATIONAL_USER'):
        # | grep to get rid of all the header lines.
        qstat_cmd = 'qstat -u '+os.getenv('USER')+' | grep '+os.getenv('USER')
        #log.info('Checking queue with: '+qstat_cmd)
        userjobs = commands.getoutput(qstat_cmd).split('\n')
        user_num_jobs = len(userjobs)
        user_num_running = len([xx for xx in userjobs if ' R ' in xx])
        user_num_queued = len([xx for xx in userjobs if ' R ' in xx])

    total_num_jobs = len(jobs)
    total_num_running = len([xx for xx in jobs if ' R ' in xx])
    total_num_queued = len([xx for xx in jobs if ' R ' in xx])
    
    dict_num_jobs = {}
    dict_num_running = {}
    dict_num_queued = {}

    dict_txt = ''
    user_txt = ''

    for job_name in job_limits_RandQ.keys()+job_limits_Ronly.keys():
        # Grep qstat for example: qstat | grep "Job_Name =.*viirs_ssec" -A 10 | grep "job_state = R"
        # Can't get full job name in any listing but qstat -f, and then everything is on separate line..
        # so grep for running jobs after grepping for job name
        #qstat_cmd = '/usr/bin/qstat | grep "'+job_name+'.*[QR] '+queue_name+'"'
        # Also, if we are never timing out (ie, process_overpass), include queued and running jobs in list
        #   for frequent revisit downloaders just count running (they will just fail, then get kicked off
        #   again if the queue is full when they finally get to R).  viirsrdr need to be limited by Q and R, 
        # only_check_running is a list passed in that includes all job_name strings that should include
        #   only running jobs when counting.  Everything else should count running and queued
        # On beryl, qsub fails outright if qsubname is longer than 15 characters.
        # Probably want to handle this better at some point.
        grep_name = job_name[0:14]
        if not give_up_time or job_name not in job_limits_Ronly.keys():
            # Must include queued jobs for viirsrdr converter... 
            qstat_cmd = 'qstat -f | grep "Job_Name =.*'+grep_name+'" -A 10 | grep -E "job_state = R|job_state = Q"'
        else:
            # Leave out queued jobs for downloaders, they should all kill themselves once they start up if there are too many
            qstat_cmd = 'qstat -f | grep "Job_Name =.*'+grep_name+'" -A 10 | grep -E "job_state = R"'
        log.info('Checking queue with: '+qstat_cmd)
        jobs = commands.getoutput(qstat_cmd).split('\n')
        # Was always returning at least 1 for each job_name because '' was being counted 
        jobs = [xx for xx in jobs if xx]
        log.debug('Jobs:'+str(jobs)+'done')

        if job_name not in dict_num_jobs.keys():
            dict_num_jobs[job_name] = len(jobs)
            dict_num_running[job_name] = len([xx for xx in jobs if 'job_state = R' in xx])
            dict_num_queued[job_name] = len([xx for xx in jobs if 'job_state = Q' in xx])
        else:
            dict_num_jobs[job_name] += len(jobs)
            dict_num_running[job_name] += len([xx for xx in jobs if 'job_state = R' in xx])
            dict_num_queued[job_name] += len([xx for xx in jobs if 'job_state = Q' in xx])
        dict_txt += ' and '+str(dict_num_jobs[job_name])+' (R'+str(dict_num_running[job_name])+' Q'+str(dict_num_queued[job_name])+') '+job_name+' jobs'
    if user_num_jobs:
        user_txt = ' and '+str(user_num_jobs)+' user '+os.getenv('USER')+' jobs '
    total_txt = str(total_num_jobs)+' jobs(R'+str(total_num_running)+')'
        
    log.interactive('  '+total_txt+user_txt+dict_txt+' running on '+queue_box+' currently')

    wait_txt = []


    # This should all be done in one shot using max_other_jobs_dict
    dict_jobs_over = False
    dict_running_jobs_over = {}
    total_jobs_over = False
    user_jobs_over = False
    for job_name in job_limits_Ronly.keys()+job_limits_RandQ.keys():
        if job_name in job_limits_Ronly.keys() and dict_num_running[job_name] >= job_limits_Ronly[job_name]:
            dict_jobs_over = True
            dict_running_jobs_over[job_name] = True
        elif job_name not in job_limits_Ronly.keys() and dict_num_jobs[job_name] >= job_limits_RandQ[job_name]:
            dict_jobs_over = True
    if total_num_jobs >= max_total_jobs:
        total_jobs_over = True
    if user_num_jobs >= max_user_jobs:
        user_jobs_over = True
   
    if dict_jobs_over or total_jobs_over or user_jobs_over: 
        log.debug(give_up_time)
        log.debug(current_sleep_time)
        if give_up_time is not None and int(current_sleep_time) >= int(give_up_time):
            log.interactive('      Giving up, we\'ve been waiting longer than give_up_time '+str(give_up_time))
            return False
        elif give_up_time is not None and dict_running_jobs_over:
            log.interactive('      Giving up, maxed out on running jobs: '+str(dict_running_jobs_over.keys()))
            # 20160315 Previously I had passed have_max_running to wait_for_queue - waited until the next time 
            # through to kill.  Not sure why, or if necessary. Try this simplified version, to see if it works..
            # Basically we want to kill it right away if we are limiting on only running, because everyone 
            # could end up in R state, with everything just waiting for the queue to clear and not doing anything.
            # Maybe used have_max_running so they wouldn't all kill themselves at the same time ? But that should
            # just push it back 30s, so they all killed themselves 30s later at the same time...
            return False
        else:
            log.interactive('      We\'ve been waiting for '+str(current_sleep_time)+' seconds, giving up after '+str(give_up_time))

        
        # have_max_running = False
        for job_name in job_limits_Ronly.keys()+job_limits_RandQ.keys():
            if job_name in job_limits_Ronly.keys() and dict_num_running >= job_limits_Ronly[job_name]:
                wait_txt += [' running '+job_name+' jobs to drop below '+str(job_limits_Ronly[job_name])]
                # have_max_running = False
            elif job_name not in job_limits_Ronly.keys() and dict_num_jobs >= job_limits_RandQ[job_name]:
                wait_txt += [' queued and running '+job_name+' jobs to drop below '+str(job_limits_RandQ[job_name])]
        if total_num_jobs >= max_total_jobs:
            wait_txt = [' total jobs on '+queue_box+' to drop below '+str(max_total_jobs)]
        if user_num_jobs >= max_user_jobs:
            wait_txt = [' total '+os.getenv('USER')+' jobs on '+queue_box+' to drop below '+str(max_user_jobs)]
        log.interactive('      Waiting for '+' and '.join(wait_txt)+' ...')
        time.sleep(sleeptime)
        current_sleep_time = current_sleep_time + sleeptime
        return wait_for_queue(sleeptime=sleeptime,
                              give_up_time=give_up_time,
                              current_sleep_time = current_sleep_time,
                              queue=queue,
                              job_limits_RandQ=job_limits_RandQ,
                              job_limits_Ronly=job_limits_Ronly,
                              max_total_jobs=max_total_jobs,
                              max_user_jobs=max_user_jobs,
                              #have_max_running=have_max_running,
                             )

    return True

def qsub(command,
                 cmdargs,
                 **kwargs
                ):
    '''If $QSUB is set in the user's environment, will execute a
    command through the script defined in $QSUB
    Also capable of passing a data file with the command and will
    clean up said data file after the spawned process has completed.

    Documentation for PBS's qsub is available at:
        http://linux.die.net/man/1/qsub

    Syntax:
        output = qsub(command, args, **kwargs)

    +-------------+--------------------------------------------------------------------------+
    | Parameters: |                                                                          |
    +=============+==========================================================================+
    | command     | Name of the command to execute on the remote server (string)             |
    +-------------+--------------------------------------------------------------------------+
    | cmdargs     | List of positional arguments to be passed to `command` (list of strings) |
    +-------------+--------------------------------------------------------------------------+

    +-------------------+----------------------------------------------------------------------------+
    | Keywords:         |                                                                            |
    +===================+============================================================================+
    | queue             | Name of the queue to which the job should be submitted. (string)           |
    |                   | sets `qsub -q <queue>`                                                     |
    |                   | Default: `None`                                                            |
    +-------------------+----------------------------------------------------------------------------+
    | name              | Name of the job for use in the queue. (string)                             |
    |                   | sets `qsub -N <name>`                                                      |
    |                   | Default: `command`                                                         |
    +-------------------+----------------------------------------------------------------------------+
    | outfile           | Fully qualified filename to which stdout will be written. (string)         |
    |                   | Sets `qsub -o <outfile>`                                                   |
    |                   | Default: `None`                                                            |
    +-------------------+----------------------------------------------------------------------------+
    | errfile           | Fully qualified filename to which stderr will be written. (string)         |
    |                   | Sets `qsub -e <errfile>`                                                   |
    |                   | Default: `None`                                                            |
    +-------------------+----------------------------------------------------------------------------+
    | resource_list     | Defines the resources that are required by the job and establishes a limit |
    |                   | to the amount of resource that can be consumed. If not set for a           |
    |                   | generally available resource, such as CPU time, the limit is infinite.     |
    |                   | The resource_list argument is of the form:                                 |
    |                   | resource_name[=[value]][,resource_name[=[value]],...]                      |
    |                   | For more information on the use of this keyword, see the torque            |
    |                   | documentation available at:                                                |
    |                   | docs.adaptivecomputing.com/torque/4-0-2/Content/topics/commands/qsub.htm   |
    |                   | The resource list is specified by the -l option.                           |
    +-------------------+----------------------------------------------------------------------------+
    | join              | Join stdout and stderr into the same stream. Will go to `outfile`.         |
    |                   | Default: `True`                                                            |
    +-------------------+----------------------------------------------------------------------------+
    | remotestageinfile | Fully qualified path to a stage in file on the remote host.                |
    |                   | Required if `localstageinfile` is set.                                     |
    |                   | NOTE: In this case, the "remote" host is the box on which                  |
    |                   | `qsub` is called.                                                          |
    |                   | Sets `qsub -W STAGEIN=<remotestageinfile>@<callingbox>:<localstageinfile>` |
    +-------------------+----------------------------------------------------------------------------+
    | localstageinfile  | Fully qualified path to location where stagein file should be placed       |
    |                   | on the local host.                                                         |
    |                   | Required if `remotestageinfile` is set.                                    |
    |                   | NOTE: In thise case, the "local" host is the box on which `command`        |
    |                   | will be executed.                                                          |
    |                   | Sets `qsub -W STAGEIN=<remotestageinfile>@<callingbox>:<localstageinfile>` |
    +-------------------+----------------------------------------------------------------------------+
    '''
    kwargs['queue'] = kwargs.get('queue', None)
    kwargs['name'] = kwargs.get('name', None)
    kwargs['outfile'] = kwargs.get('outfile', None)
    kwargs['errfile'] = kwargs.get('errfile', None)
    kwargs['resource_list'] = kwargs.get('resource_list', None)
    kwargs['join'] = kwargs.get('join', 'oe')
    kwargs['interactive'] = kwargs.get('interactive', False)
    kwargs['remotestageinfile'] = kwargs.get('remotestageinfile', None)
    kwargs['localstageinfile'] = kwargs.get('localstageinfile', None)

    if kwargs['queue'] is not None:
        try:
            (qname, boxname) = kwargs['queue'].split('@')
        except ValueError:
            qname = kwargs['queue']
            boxname = kwargs['queue']

        if do_stagein(boxname) is False:
            log.info('Not doing stagein')
            kwargs['remotestageinfile'] = None
            kwargs['localstageinfile'] = None

    log.debug('In qsub')

    if kwargs['outfile'] is not None:
        if not os.path.isdir(os.path.dirname(kwargs['outfile'])):
            os.makedirs(os.path.dirname(kwargs['outfile']))

    if kwargs['queue'] is None:
        args = shlex.split(command+' '+' '.join(cmdargs))
        log.info('    No queue provided.  Will not qsub.  Will run on current box.')
        log.info('\n\nCOMMAND:\n'+str(args)+'\nDONE\n\n')
        subproc = Popen(args, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        out, err = subproc.communicate()
        log.interactive('COMMAND OUTPUT: %s' % out)
        if err:
            log.interactive('COMMAND ERROR: %s' % err)
    else:
        qsub = 'qsub'
        log.debug('    Using real qsub: '+qsub)

        qsub_opts = parse_opts(**kwargs)
        if not qsub_opts.has_key('-N'): qsub_opts['-N'] = os.path.basename(command)
        qsub_args = ['qsub']
        for item in qsub_opts.items(): qsub_args.extend(item)
        qsub_cmd = ' '.join(qsub_args)

        getbox_cmd = 'hostname -s'
        if gpaths['GEOIPS_SCRIPTS'] and os.path.exists(gpaths['GEOIPS_SCRIPTS']+'/getbox.sh'):
            getbox_cmd = gpaths['GEOIPS_SCRIPTS']+'/getbox.sh'

        job_cmd = command+' '+' '.join(cmdargs)

        cmd = '; '.join([getbox_cmd, job_cmd])

        #******************************
        #This section should only be used as long as we have to SSH
        #******************************

#        #Construct a single command and replace " with \"
#        getbox_cmd = 'source '+os.getenv('UTILSDIR')+'/getbox.csh'
#        job_cmd = command+' '+' '.join(cmdargs)
#        job_cmd = replace_environment_variables(job_cmd)
#        #job_cmd = getbox_cmd+'; '+command+' '+' '.join(cmdargs)
#        #job_cmd.replace('"', '\\"')
#        #cmd = '; '.join([getbox_cmd, job_cmd]) + ' | ' + qsub_cmd

#        log.interactive('Opening ssh tunnel to %s' % boxname)
#        ssh_proc = Popen(['ssh', '-q', boxname], stdin=PIPE, stdout=PIPE, stderr=PIPE)
#        ssh_proc.stdin.write('echo Qsub Hostname: `hostname`\n')
#        #ssh_proc = Popen(['ssh', boxname], stdin=PIPE, stdout=PIPE, stderr=PIPE)
#
#        #******THIS DID NOT WORK DUE TO THE ISSUE DESCRIBED HERE:
#        #      https://lists.sdsc.edu/pipermail/npaci-rocks-discussion/2002-October/000592.html
#        #******Worked fine for bash, but failed for tcsh due to lack of stty settings
#        ssh_proc.stdin.write(qsub_cmd+' << EOF\n')
#        #log.interactive('Calling: %s' % getbox_cmd)
#        #ssh_proc.stdin.write(getbox_cmd+'\n')
#        ssh_proc.stdin.write(job_cmd+'\n')
#        ssh_proc.stdin.write('EOF\n')
#        #******
#
#        #out, err = ssh_proc.communicate()
#        #log.interactive('SSH OUTPUT: %s' % out)
#        #if err:
#        #    log.interactive('SSH error: %s' % err)

        #******************************
        #The section below should be used if we quit SSHing prior to qsub
        #******************************


        #This deserves an explanation.
        #First we open a qsub process whose stdin is set to PIPE
        #The process has all of the various qsub options set,
        #   but does not yet have a job to send to a node.
        qsub_proc = Popen(qsub_args, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        #The communicate method of the process allows us to obtain
        #   a tuple of stdout and stderr, but also allows us to pass
        #   stdin through the input keyword.
        #Here we pass the command we wish to add to the PBS queue.
        out, err = qsub_proc.communicate(input=cmd)

        log.interactive('\nQSUB CALL: %s\nSYSTEM CALL: %s\nQSUB OUTPUT: %s\n' % (qsub_cmd,cmd,out))
        if err:
            log.interactive('\nQSUB CALL: %s\nSYSTEM CALL: %s\nQSUB OUTPUT: %s\nQSUB ERROR: %s' % (qsub_cmd,cmd,out,err))

def replace_environment_variables(arg):
    '''Given a string, will replace a set of expanded environment variables
    with their unexpanded variable name.  This is to avoid conflicts between
    environments when using multiple clusters.
    '''
    evars = {'GEOIPS': gpaths['GEOIPS'],
             'SHAREDSCRATCH': gpaths['SHAREDSCRATCH'],
             'LOCALSCRATCH': gpaths['LOCALSCRATCH'],
             'SCRATCH': gpaths['SCRATCH'],
             'PROCSDIR': os.getenv('PROCSDIR'),
            }
    for var, path in evars.iteritems():
        arg = arg.replace(path, '$'+var)
    return arg

def do_stagein(boxname):
# gethostname returns ie kahuna.nrlmry.navy.mil
    curr_boxname = gethostname()
    #if (('kahuna' in curr_boxname) or ('compute' in curr_boxname)) and ('kahuna' in boxname):
    #    return False
    #else:
    #    return True
    return True

def parse_opts(**kwargs):
    '''Parses a dictionary to produce a string of options to be passed to qsub.
    Note: I tried to be fancy here and trim it to a small amount of code,
    but it became very combersome.  Just doing it the long way is better.'''
    #opts = {k:v for k, v in kwargs.items() if v is not None}
    opts = {}
    if kwargs['queue'] is not None:
        opts['-q'] = kwargs['queue']
    if kwargs['name'] is not None:
        opts['-N'] = kwargs['name']
    if kwargs['outfile'] is not None:
        opts['-o'] = kwargs['outfile']
    if kwargs['errfile'] is not None:
        opts['-e'] = kwargs['errfile']
    if kwargs['join'] is not None:
        if kwargs['join'] is True:
            opts['-j'] = 'oe'
        else:
            opts['-j'] = kwargs['join']
    if kwargs['resource_list'] is not None:
        opts['-l'] = kwargs['resource_list']
    if (kwargs['remotestageinfile'] and kwargs['localstageinfile']):
        opts['-W'] = get_stagein_opt(kwargs['remotestageinfile'], kwargs['localstageinfile'])
#Add to these if you want to use them.  THis is getting stupid on a Friday!!!
#    if kwargs['seconds'] is not None:
#        opts['-b'] = kwargs['seconds']
#    if kwargs['checkpoint_options'] is not None:
#        opts['-c'] = kwargs['checkpoint_options']
#    if kwargs['work_dir'] is not None:
#        opts['-d'] =
    if kwargs['interactive'] is True:
        opts['I'] = ''
    return opts

def get_stagein_opt(rf, lf):
    rf = os.path.abspath(rf)
    lf = os.path.abspath(lf)
    hn = gethostname().split('.')[0]
    if not os.path.isfile(rf):
        raise IOError('stagein file does not exist: %s' % rf)
    return 'STAGEIN=%s@%s:%s' % (rf, hn, lf)

def __parse_date_time_opt(str):
    def makepair(arr):
        if len(arr) == 2:
            return ''.join(arr)
        elif len(arr) == 1:
            return
    temp = str.split('.')
    dt = list(temp[0])
    dt.reverse()

    parts = {
             'sec': temp[1] if len(temp) > 1 else '',
             'min': ''.join(dt[0:2]) if len(dt[0:2]) == 2 else None,
             'hr': ''.join(dt[2:4]) if len(dt[2:4]) == 2 else None,
             'day': ''.join(dt[4:6]) if len(dt[4:6]) == 2 else None,
             'mon': ''.join(dt[6:8]) if len(dt[6:8]) else None,
             'yr': ''.join(dt[8:10]),
             'cen': ''.join(dt[10:12]),
            }

def __parse_checkpoint_options_opt(str):
    choices = ['none', 'enabled', 'shutdown', 'periodic', 'interval=', 'depth=', 'dir=']
    long_choices = ['none', 'enabled', 'shutdown', 'periodic', 'interval=minutes', 'depth=number', 'dir=path']
    parts = str.split('=')
    if len(parts) > 1:
        type = parts[0]+'='
    else:
        type = parts[0]
    if type in choices:
        return str
    else:
        raise argparse.ArgumentTypeError('invalid choice: %s (choose from %s)' % (str, ', '.join(long_choices)))



if __name__ == '__main__':
    root_logger = root_log_setup()

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    common = parser.add_argument_group(title='Commonly used arguments',
                                       description=textwrap.dedent('''\
                                            This section provides a description of arguments commonly used by
                                            GeoIPS and that may be commonly used by the user directly.  Other
                                            arguments specified below are available for completeness and are
                                            only recommended if the user is SURE that they know what they are
                                            doing.
                                            ''')
                                       )
    common.add_argument('-q', '--queue', default=os.getenv('DEFAULT_QUEUE'),
                        help=textwrap.dedent('''\
                             Defines the destination of the job.  Unlike the PBS qsub command, this option
                             can only be specified as a queue at a server (e.g. queue_name@server_name).

                             This script will submit the given command  to the server defined by the queue
                             argument.  If the destination is a routing queue, the job may be routed by the
                             server to a new queue.

                             If the -q option is not specified, the qsub command will submit the script to
                             the default server.  This is determined by the PBS_DEFAULT environment variable.

                             If the -q option is specified, unlike the command line PBS qsub command, it must
                             be in the form:
                                queue_name@server_name
                             ''')
                        )

    common.add_argument('-n', '-N', '--name', default=None,
                        help=textwrap.dedent('''\
                             Declares a name for the job.  The name specified may be up to 15 characters long.
                             It must consist of printable, non white space characters.  The first character
                             must be aphabetic.

                             If the -n option is not specified, the job name will be the base name of the
                             command to be executed on the remote host.
                             ''')
                        )

    common.add_argument('-o', '--outfile', default=None,
                        help=textwrap.dedent('''
                             Defines the path to be used for the standard output stream of the batch job.
                             The path argument is of the form:

                                [hostname:]path_name

                            Where hostname is the name of a host to which the file will be returned and
                            path_name is the path name on that hose in the syntax recognized by POSIX.
                            The argument will be interpreted as follows:

                                path_name
                                    Where path_name is not an absolute path name, then the qsub command
                                    will expand the path name relative to the current working directory
                                    of the command.  The command will supply the name of the host upon
                                    which it is executing for the hostname component.
                                hostname:path_name
                                    Where path_name is not an absolute path name, then the qsub command
                                    will NOT expand the path name relative to the current working directory
                                    of the command.  On delivery of the standard error, the path name will
                                    be expanded relative to the users home directory on the hostname system.
                                path_name
                                    Where path_name specifies an absolute path name, then the qsub will
                                    supply the name of the host on which it is executing for the hostname.
                                hostname:path_name
                                    Where path_name specifies an absolute path name, the path will be used
                                    as specified.
                            ''')
                        )

    common.add_argument('-e', '--errfile', default=None,
                        help=textwrap.dedent('''\
                             Defines the path to be used for the standard error stream of the batch job.
                             The path argument is of the form:

                                [hostname:]path_name

                            Where hostname is the name of a host to which the file will be returned and
                            path_name is the path name on that hose in the syntax recognized by POSIX.
                            The argument will be interpreted as follows:

                                path_name
                                    Where path_name is not an absolute path name, then the qsub command
                                    will expand the path name relative to the current working directory
                                    of the command.  The command will supply the name of the host upon
                                    which it is executing for the hostname component.
                                hostname:path_name
                                    Where path_name is not an absolute path name, then the qsub command
                                    will NOT expand the path name relative to the current working directory
                                    of the command.  On delivery of the standard error, the path name will
                                    be expanded relative to the users home directory on the hostname system.
                                path_name
                                    Where path_name specifies an absolute path name, then the qsub will
                                    supply the name of the host on which it is executing for the hostname.
                                hostname:path_name
                                    Where path_name specifies an absolute path name, the path will be used
                                    as specified.
                            ''')
                        )

    common.add_argument('-j', '--join', default='oe', choices=['oe', 'eo', 'n'],
                        help=textwrap.dedent('''\
                             Declares if the standard error stream of the job will be merged with the standard
                             output stream of the job.  Unlike the command-line PBS qsub command, -j defaults
                             to redirecting stderr to stdout.

                             An option argument value of 'oe' directs that the two streams will be merged,
                             intermixed, as standard output.  An option argument value of eo directs that the
                             two streams will be merged, intermixed, as standard error.

                             If the join argument is 'n', the two streams will be two separate files.
                             ''')
                        )

    stage = parser.add_argument_group(title='File staging options',
                                      description=textwrap.dedent('''\
                                            The following arguments are used for staging files for copy to
                                            and from the remote host via scp protocall.  These options must
                                            be used together.

                                            Regardless of the direction of copy, the term "local" refers to
                                            the execution host, while the term "remote" refers to any other
                                            machine.  This is slightly counterintuitive as "local" does not
                                            refer to the system on which qsub is being executed, but instead
                                            the system on which the queued job will be run.

                                            For these options, the "remote host" is assumed to be the cluster's
                                            head node.
                                            ''')
                                      )
    stage.add_argument('-L', '--localstageinfile', default=None,
                       help=textwrap.dedent('''\
                            Specifies where a file passed to the execution host via the -R option
                            should be placed on the execution host.
                            A fully qualified path name must be specified.
                            ''')
                       )
    stage.add_argument('-R', '--remotestageinfile', default=None,
                       help=textwrap.dedent('''\
                            Specifies a file that should be passed to the execution host.
                            If specified, -L must also be specified.
                            ''')
                       )

    other = parser.add_argument_group(title='Other arguments (UNTESTED! and less common)',
                                      description=textwrap.dedent('''\
                                            WARNING: NONE OF THESE HAVE BEEN TESTED! Use at your own risk!

                                            This section provides descriptions for all available, but less
                                            commonly used options.  The user should be absolutely sure that
                                            they know what they are doing prior to using any of these options
                                            seeing as the author of this script has not used them yet.
                                            ''')
                                      )
#Started adding additional arguments, but this seems pointless.  None of these will get used.
#Add as required later...
#    parser.add_argument('-a', '--date_time', default=None, 
#    parser.add_argument('-A', '--account_string', default=None, 
#                        help=textwrap.dedent('''\
#                             Defines the account string associated with the job.
#                             The account_string is an undefined string of characters
#                             and is interpreted by the server which executes the job.
#                             See section 2.7.1 of the PBS ERS.
#                             ''')
#                       )
#    other.add_argument('-b', '--seconds', default=None,
#                        help=textwrap.dedent('''\
#                             Defines the maximum number of seconds qsub will block
#                             attempting to contact pbs_server. If pbs_server is down,
#                             or for a variety of communication failures, qsub will
#                             continually retry connecting to pbs_server for job submission.
#                             This value overrides the CLIENTRETRY parameter in torque.cfg.
#                             This is a non-portable TORQUE extension. Portability-minded
#                             users can use the PBS_CLIENTRETRY environmental variable.
#                             A negative value is interpreted as infinity. The default is 0.
#                             ''')
#                       )
#    other.add_argument('-c', '--checkpoint_options', default=None, type=__parse_checkpoint_options_opt,
#                        help=textwrap.dedent('''\
#                             Defines the options that will apply to the job.
#                             If the job executes upon a host which does not support checkpoint,
#                             these options will be ignored.
#
#                             Valid checkpoint options are:
#
#                                 none
#                                     No checkpointing is to be performed.
#                                 enabled
#                                     Specify that checkpointing is allowed but must be explicitly invoked by
#                                     either the qhold or qchkpt commands.
#                                 shutdown
#                                     Specify that checkpointing is to be done on a job at pbs_mom shutdown.
#                                 periodic
#                                     Specify that periodic checkpointing is enabled. The default interval is
#                                     10 minutes and can be changed by the $checkpoint_interval option in the
#                                     mom config file or by specifying an interval when the job is submitted
#                                 interval=minutes
#                                     Checkpointing is to be performed at an interval of minutes, which is the
#                                     integer number of minutes of wall time used by the job. This value must
#                                     be greater than zero.
#                                 depth=number
#                                     Specify a number (depth) of checkpoint images to be kept in the checkpoint
#                                     directory.
#                                 dir=path
#                                     Specify a checkpoint directory (default is /var/spool/torque/checkpoint).
#                             ''')
#                       )
##    parser.add_argument('-C', '--directive_prefix')
#    other.add_argument('-d', '--work_dir', default=None,
#                        help=textwrap.dedent('''\
#                             Defines the working directory path to be used for the job.  If the -d option
#                             is not specified , the default working directory is the home directory.
#                             This option sets the environment variable PBS_O_INITDIR.
#                             ''')
#                        )
#    other.add_argument('-D', '--root_dir', default=None,
#                        help=textwrap.dedent('''\
#                             Defines the root directory to be used for the job.  This option sets the
#                             environment variable PBS_O_ROOTDIR.
#                             ''')
#                        )
#    other.add_argument('-f', '--fault_tolerant', default=None, action='store_true',
#                        help=textwrap.dedent('''\
#                             Job is made fault tolerant. Jobs running on multiple nodes are periodically
#                             polled by mother superior. If one of the nodes fails to report, the job is
#                             canceled by mother superior and a failure is reported. If a job is fault
#                             tolerant, it will not be canceled based on failed polling (no matter how many
#                             nodes fail to report). This may be desirable if transient network failures are
#                             causing large jobs not to complete, where ignoring one failed polling attempt
#                             can be corrected at the next polling attempt.
#                             ''')
#                        )
#    other.add_argument('-H', '--user_hold', default=None, action='store_true',
#                        help=textwrap.dedent('''\
#                             Specifies that a user hold be applied to the job as submission time.
#                             This is the same argument as the command-line PBS qsub command's '-h' and was
#                             switched to '-H' to avoid conflict with the '--help' option.
#                             ''')
#                        )
    other.add_argument('-I', '--interactive', default=False, action='store_true',
                        help=textwrap.dedent('''\
                             Declates that the job is to be run "interactively". The job will be queued and
                             schedules as any PBS batch job, but when executed, the standard input, and error
                             streams of the job are connected through the qsub to the terminal session in which
                             qsub is running.  Interactive jobs are forced to not rerunable. See the "Extended
                             Description" paratraph for additional information on interactive jobs.
                             ''')
                        )
#    other.add_argument('-k', '--keep', default=None, choices=['e', 'o', 'eo', 'oe', 'n'],
#                        help=textwrap.dedent('''\
#                             Defines which (if either) of standard output or standard error will be retained
#                             on the exectution host.  If set for a stream, this option overrides the path name
#                             for that stream.  If not set, neither stream is retained on the execution host.
#
#                             Options:
#                                e
#                                    The standard error stream is to be retained on the execution host.  The
#                                    stream will be placed in the home directory of the user under whose id
#                                    the job executed.  The file name will be the default file name given by:
#                                        job_name.esequence
#                                    where job-name is the name specified for the job, and sequence is the
#                                    sequence number component of the job identifier.
#                                o
#                                    The standard output stream is to be retained on the exectution host.  The
#                                    stream will be placed in the home directory of the user under whose id
#                                    the job executed.  The file name will be the default file name given by:
#                                        job_name.osequence
#                                    where job_name is the name specified for the job, and sequence is the
#                                    sequence number component of the job identifier.
#                                eo
#                                    Both streams will be retained.
#                                oe
#                                    Both streams will be retained.
#                                n
#                                    Neither stream is retained.
#                             ''')
#                        )
    other.add_argument('-l', '--resource_list', default=None,
                        help=textwrap.dedent('''\
                             Defines the resources that are required by the job and establishes a limit to the
                             amount of resource that can be consumed.  If not set for a generally available
                             resource, such as CPU time, the limit is infinite.  Any number of resources can
                             be specified at one time by specifying multiple arguments of the form:

                                resource_name[=[value]]

                            separated by spaces.

                            For more information on requesting resources, please see:

                                http://www.clusterresources.com/torquedocs/2.1jobsubmission.shtml#resources
                            ''')
                        )
#    other.add_argument('-m', '--mail_options', default=None,
#                        help=textwrap.dedent('''\
#                             Defines the set of contitions under which the execution server will send a mail
#                             message about the job.  The mail_options argument is a string which consists of
#                             either the single character 'n', or one or more of the characters 'a', 'a',
#                             and 'e'.
#
#                             If the character 'n' is specified, no normal mail is sent.  Mail for job cancels
#                             and other events outside of normal job processing are still sent.
#
#                             For the letters 'a', 'b', and 'e':
#                                a
#                                    mail is sent when a job is aborted by the batch system.
#                                b
#                                    mail is sent when a job begins execution.
#                                e
#                                    mail is sent when a job terminates.
#                            if the -m option is not specified, mail will be sent if the job is aborted.
#                            ''')
#                        )
#    other.add_argument('-M', '--mail_user_list', nargs='*', default=None,
#                        help=textwrap.dedent('''\
#                             Declares the list of users to whom mail is sent by the execution server when it
#                             sends mail about the job.
#
#                             The argument is comprised of as many emails as nessicary, separated by spaces.
#                             The emails must be of the form:
#
#                                user[@host]
#
#                             If unset, the list defaults to the submitting user at the qsub host, i.e. the
#                             job owner.
#                             ''')
#                        )
#    other.add_argument('-p', '--priority', default=None,
#                        help=textwrap.dedent('''\
#                             Defines the priority of the job.  The priority argument must be an integer
#                             between -1024 and +1024 inclusive.  The default is no priority which is equivalent
#                             to a priority of zero.
#                             ''')
#                        )
#    other.add_argument('-P', '--user_proxy', default=None,
#                        help=textwrap.dedent('''\
#                             ROOT ONLY
#                             Allows a root user to submit a job as another user.  TORQUE treats proxy jobs as
#                             though the jobs were submitted by the supplied username.  This feature is available
#                             in TORQUE 2.4.7 and later, however, TORQUE 2.4.7 does not have the ability to supply
#                             the [:group] option.  The [:group] option is available in TORQUE 2.4.8 and later.
#                             ''')
#                        )
#    other.add_argument('-S', '--path_list', nargs='*', default=None,
#                        help=textwrap.dedent('''\
#                             Declares the shell that interprets the job script.  Multiple arguments may be
#                             specified, separated by spaces.  Each argument is of the form:
#
#                                path[@host]
#
#                            Only one path may be specified for any host named.  Only one path may be specified
#                            without the corresponding host name.  the path selected will be the one with the
#                            host name that matched the name of the execution host.  If no matching host is found
#                            then the path specified without a host will be selected, if present.
#
#                            If the -S option is not specified, the option argument is the null string, or no
#                            entry from the path_list is selected.  The execution will use the users login
#                            shell on the execution host.
#                            ''')
#                        )
#    other.add_argument('-t', '--array_request', nargs='*', default=None,
#                        help=textwrap.dedent('''\
#                             Specifies the task ids of a job array.  Single task arrays are allowed.
#
#                             The array_request argument is an integer id or a range of integers.  Multiple ids
#                             or id ranges can be combined in a space delimited list.  Examples:
#
#                                -t 1 10
#                                -t 1-100
#                                -t 1 10 50-100
#
#                            An optional slot limit can be specified to limit the amount of jobs than can run
#                            concurrently in the job array.  The default value is unlimited.  The slot limit
#                            must be the last thing specified in the array_request and is delimited from the
#                            array by a percent sign (%%).
#
#                                qsub command -t 0-299%%5
#
#                            This sets the slot limit to 5.  Only 5 jobs from this array can run at the same time.
#
#                            You can use qalter to modify slot limits on an array.  The server parameter
#                            max_slot_limit can be used to set a global slot limit policy.
#                            ''')
#                        )
#    other.add_argument('-u', '--user_list', nargs='*', default=None,
#                        help=textwrap.dedent('''\
#                             Defines the suer name under which the job is to run on the execution system.
#
#                             The user_list argument is of the form:
#
#                                user[@host]
#
#                            And may be specified multiple times, separated by spaces.  Only one user name may be
#                            given per specified host.  Only one of the user specifications may be supplied
#                            without the corresponding host specification.  That user name will be used for
#                            execution on any host not named in the argument list.  If unset, the user list
#                            defaults to the user who is running qsub.
#                            ''')
#                        )
#    other.add_argument('-v', '--variable_list', default=None,
#                        help=textwrap.dedent('''\
#                             Expands the list of environment variables that are exported to the job.
#
#                             In addition to the variables described in the "Destination" section above,
#                             variable_list names environment variables from the qsub command environment
#                             which are made available when the job executes.  The variable_list is a space
#                             delimited list of strings of the form variable or variable=value.  These variables
#                             and their values are passed the the job.
#                             ''')
#                        )
#    other.add_argument('-V', '--whole_environment', default=None, action='store_true',
#                        help=textwrap.dedent('''\
#                             Declares that all environment variables in the qsub commands environment are to be
#                             exported to the batch job.
#                             ''')
#                        )
#    other.add_argument('-W', '--additional_attributes', nargs='*', default=None,
#                        help=textwrap.dedent('''\
#                             The -W option allows for the specification of additional job attributes.  The
#                             general syntax of the -W option is of the form:
#
#                                -W attr_name=attr_value [attr_name=attr_value [...]]
#
#                            where each attribut/value pair is separated by a space.  Note, if whitespace
#                            occurs anywhere within the option argument string or the equal sign (=) occurs
#                            within an attribute_value string, then the string must be quoted.
#
#                            Note that the stagein option is available via the --remotestageinfile and
#                            --localstageinfile options for convenience.
#
#                            PBS currently supports MANY arguments to the -W option.  Please see
#
#                                http://www.clusterresources.com/torquedocs/commands/qsub.shtml#W
#
#                            for a complete list.
#                            ''')
#                        )
#    other.add_argument('-X', '--X11', default=None,
#                        help=textwrap.dedent('''\
#                             Enables X11 forwarding.  The DISPLAY environment variable must be set.
#                             ''')
#                        )
#    other.add_argument('-z', '--noid', default=None, action='store_true',
#                        help=textwrap.dedent('''\
#                             Directs that the qsub command is not to write the job identifier to the command's
#                             standard output.
#                             ''')
#                        )
    parser.add_argument('command')
    #parser.add_argument('args', nargs='*')
    # MLS 20151215
    # Store everything else as command. This creates a list. Not sure why we had stopped doing it this way before...
    # I have a dummy script in place in $UTILSDIR (/data/nrlsat/utils/nrl_qsub.sh) that just passes $@ straight 
    # through to qsub.py.  $@ loses ", so the old way was not working. This seems to work (but if you do pass something
    # with quotes, it doesn't separate it, but still seems to run?)
    # MLS 20151215
    # Ok, figured out why we don't use '*' - if we have a command that includes options...
    #parser.add_argument('command', nargs='*')
    inargs = vars(parser.parse_args())
    print inargs['command']

    #Test the args
    if bool(inargs['remotestageinfile']) != bool(inargs['localstageinfile']):
        raise argparse.ArgumentTypeError('options -R and -L are codependent and must be set together.')

    fullcommand = inargs.pop('command').split()
    executable = fullcommand[0]
    args = fullcommand[1:]
    kwargs = {}
    #for k, v in inargs.items():
    #    if v is not None:
    #        kwargs[k] = v
    kwargs = {k: v for k, v in inargs.items()}# if v is not None}

    qsub(executable, args, **kwargs)
