# -*- coding: utf-8 -*-
"""
Серверная часть агента. Запускается на сервере, открывает соединение для
получения команд из клиентской части.
"""
from openre.agent.decorators import daemonize
from openre.agent.helpers import daemon_stop
import logging
import signal
from openre.agent.server.args import parser
from openre.agent.server.server import run as _run

def run():
    args = parser.parse_args()
    @daemonize(
        args.pid_file,
        signal_map={
            signal.SIGTERM: sigterm
        }
    )
    def start():
        """
        Запуск серера
        """
        logging.info('Sart OpenRE.Agent server')
        _run()

    def stop():
        """
        Остановка серера
        """
        logging.info('Stop OpenRE.Agent server')
        daemon_stop(args.pid_file)

    if args.action == 'start':
        start()
    elif args.action == 'stop':
        stop()
    elif args.action == 'restart':
        stop()
        start()

def clean_and_exit():
    exit(0)

def sigterm(signum, frame):
    clean_and_exit()

