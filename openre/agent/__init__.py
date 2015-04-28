# -*- coding: utf-8 -*-
"""
OpenRE.Agent - агент для запуска доменов.
"""
import signal, syslog
import daemon as _daemon
from openre.agent import console, command_line
from lockfile.pidlockfile import PIDLockFile
from lockfile import AlreadyLocked, LockTimeout
import os
import time

def run(daemon=True):
    args = command_line.parser.parse_args()

    pidfile = PIDLockFile(args.pid_file, timeout=-1)
    def start():
        print "Start OpenRE.Agent."
        if not daemon:
            console.run()
            clean_and_exit()

        # clean old pids
        pidfile = PIDLockFile(args.pid_file, timeout=-1)
        try:
            pidfile.acquire()
            pidfile.release()
        except (AlreadyLocked, LockTimeout):
            try:
                os.kill(pidfile.read_pid(), 0)
                print 'Process already running!'
                exit(1)
            except OSError:  #No process with locked PID
                pidfile.break_lock()

        pidfile = PIDLockFile(args.pid_file, timeout=-1)

        context = _daemon.DaemonContext(
            pidfile=pidfile
        )

        context.signal_map = {
            signal.SIGTERM: sigterm
        }

        context.open()
        syslog.syslog("OpenRE.Agent START")
        with context:
            console.run()
        clean_and_exit()

    def stop():
        print "Stop OpenRE.Agent:",
        try:
            pid_num = pidfile.read_pid()
            os.kill(pid_num, signal.SIGTERM)
            # number of tries to check (every 1 sec) if agent is stoped
            tries = 600
            while tries:
                tries -= 1
                time.sleep(1)
                try:
                    os.kill(pid_num, 0)
                except OSError:  #No process with locked PID
                    break
            print "OK"
        except TypeError: # no pid file
            print "pid file not found"
        except OSError:
            print "not running"

    if args.action == 'start':
        start()
    elif args.action == 'stop':
        stop()
    elif args.action == 'restart':
        stop()
        start()

def clean_and_exit():
    syslog.syslog("OpenRE.Agent STOP")
    exit(0)

def sigterm(signum, frame):
    clean_and_exit()

if __name__ == "__main__":
    run(daemon=False)
