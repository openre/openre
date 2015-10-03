# -*- coding: utf-8 -*-
from functools import wraps
import daemon as _daemon
from lockfile.pidlockfile import PIDLockFile
from lockfile import AlreadyLocked, LockTimeout
import os
import logging
import signal
from openre.agent.helpers import add_action
import time


def daemonize(pid_file=None, signal_map=None, clean=None, force_daemon=False):
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
            if not pid_file and not force_daemon:
                if signal_map:
                    for key in signal_map.keys():
                        signal.signal(key, signal_map[key])
                logging.debug('Daemons pid: %s', os.getpid())
                f(*args, **kwargs)
                if clean:
                    clean()
                return
            if pid_file and pid_file not in ['-']:
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
                        exit(2)
                    except OSError:  #No process with locked PID
                        pidfile.break_lock()

                pidfile = PIDLockFile(pid_path, timeout=-1)

                context = _daemon.DaemonContext(
                    pidfile=pidfile
                )
            else:
                context = _daemon.DaemonContext()

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


def action(name=None, priority=50, namespace='default'):
    def wrapper(f):
        add_action(name or f.__name__, f, priority, namespace)
        @wraps(f)
        def wrapped(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapped
    return wrapper


class WaitTimeout(Exception):
    pass

def wait(timeout=10, period=0.5):
    """
    Ждем в течение timeout секунд, когда декорируемая функция вернет True или
    любое другое истинное значение.
    Если timeout = 0, то ждем бесконечно.
    С частотой не чаще period секунд опрашиваем декорируемую функцию на предмет
    удачного завершения.
    Если за timeout времени не полчилось дождаться удачного ответа генерируется
    исключение WaitTimeout.
    """
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            start_time = time.time()
            while True:
                if timeout and time.time() - start_time >= timeout:
                    raise WaitTimeout
                if f(*args, **kwargs):
                    return True
                time.sleep(period)
        return wrapped
    return wrapper


