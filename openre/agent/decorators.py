# -*- coding: utf-8 -*-
from functools import wraps
import daemon as _daemon
from lockfile.pidlockfile import PIDLockFile
from lockfile import AlreadyLocked, LockTimeout
import os
import logging
import signal

def daemonize(pid_file=None, signal_map=None, clean=None):
    """
    pid - if provided - then run as daemon in background,
          else - run in console
    signal_map - catch signals
    clean - run if normal exit
    """
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            logging.debug('Start daemon')
            if not pid_file:
                if signal_map:
                    for key in signal_map.keys():
                        signal.signal(key, signal_map[key])
                logging.debug('Daemons pid: %s', os.getpid())
                f(*args, **kwargs)
                if clean:
                    clean()
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
                logging.debug('Daemons pid: %s', os.getpid())
                f(*args, **kwargs)
                if clean:
                    clean()
        return wrapped
    return wrapper


