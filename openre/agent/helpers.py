# -*- coding: utf-8 -*-
import logging
import signal
from lockfile.pidlockfile import PIDLockFile
import os
import time
import argparse
import zmq

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

def mixin_log_level(parser):
    """
    Add --log-level argument in parser
    """
    def check_log_level(value):
        """
        Validate --log-level argument
        """
        if value not in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG',
                         'NOTSET']:
            raise argparse.ArgumentTypeError(
                "%s is an invalid log level value" % value)
        return value

    parser.add_argument(
        '--log-level',
        metavar='',
        type=check_log_level,
        dest='log_level',
        default=None,
        help='logging level, one of the: CRITICAL, ERROR, WARNING, INFO,' \
             ' DEBUG, NOTSET (default: none)'
    )

def parse_args(parser, *args, **kwargs):
    args = parser.parse_args(*args, **kwargs)
    if hasattr(args, 'log_level') and args.log_level:
        logging.basicConfig(
            format='%(levelname)s: %(message)s',
            level=getattr(logging, args.log_level)
        )
    return args

class AgentBase(object):
    """
    Абстрактный класс агента.
    """
    # if set to True - than register on server while init.
    register = False
    # connect to broker as a worker (so this agent is local and can reply to
    # requests)
    worker = False
    def __init__(self, config):
        self.config = config
        self.__run_user = self.run
        self.run = self.__run
        self.__clean_user = self.clean
        self.clean = self.__clean
        self.context = zmq.Context()
        self.init()

    def init(self):
        """
        Весь код инициализации здесь. Если очень нужно переопределить __init__,
        то обязательно использовать
        super(Agent, self).__init__(*args, **kwargs)
        в начале переопределенного метода
        """
        pass

    def run(self):
        """
        Код запуска агента. Этот метод необходимо переопределить.
        """
        raise NotImplementedError

    def clean(self):
        """
        Очистка при завершении работы агента. Этот метод можно переопределить.
        """

    def __run(self):
        try:
            self.__run_user()
        except Exception:
            raise
        finally:
            self.clean()

    def __clean(self):
        logging.debug('Agent cleaning')
        self.__clean_user()
        self.context.term()

    def socket(self, *args, **kwargs):
        socket = self.context.socket(*args, **kwargs)
        socket.setsockopt(zmq.LINGER, 0)
        return socket

