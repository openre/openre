# -*- coding: utf-8 -*-
import logging
import signal
from lockfile.pidlockfile import PIDLockFile
import os
import time

def daemon_stop(pid_file=None):
    """
    If pid is provided - then run try to stop daemon.
    Else - just return.
    """
    logging.debug('Stop daemon')
    if not pid_file:
        logging.debug('No pid file provided - nothing to stop')
        return
    pid_path = os.path.abspath(pid_file)
    pidfile = PIDLockFile(pid_path, timeout=-1)
    try:
        pid_num = pidfile.read_pid()
        os.kill(pid_num, signal.SIGTERM)
        # number of tries to check (every 1 sec) if agent is stoped
        tries = 600
        success = False
        while tries:
            tries -= 1
            time.sleep(1)
            try:
                os.kill(pid_num, 0)
            except OSError:  #No process with locked PID
                success = True
                break
        if success:
            logging.debug('Daemon successfully stopped')
        else:
            logging.warn('Unable to stop daemon')

    except TypeError: # no pid file
        logging.debug('Pid file not found')
    except OSError:
        logging.debug('Process not running')


