# -*- coding: utf-8 -*-
from functools import wraps
import daemon as _daemon
from lockfile.pidlockfile import PIDLockFile
from lockfile import AlreadyLocked, LockTimeout
import os
import logging

def daemonize(pid_file=None, signal_map=None):
    """
    If pid is provided - then run as daemon in background.
    Else - run in console.
    """
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            logging.debug('Start daemon')
            if not pid_file:
                f(*args, **kwargs)
                return
            pid_path = os.path.abspath(pid_file)

            # clean old pids
            pidfile = PIDLockFile(pid_path, timeout=-1)
            try:
                pidfile.acquire()
                pidfile.release()
            except (AlreadyLocked, LockTimeout):
                try:
                    os.kill(pidfile.read_pid(), 0)
                    logging.warn('Process already running!')
                    exit(1)
                except OSError:  #No process with locked PID
                    pidfile.break_lock()

            pidfile = PIDLockFile(pid_path, timeout=-1)

            context = _daemon.DaemonContext(
                pidfile=pidfile
            )

            if signal_map:
                context.signal_map = signal_map

            context.open()
            with context:
                f(*args, **kwargs)
        return wrapped
    return wrapper


