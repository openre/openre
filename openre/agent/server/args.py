# -*- coding: utf-8 -*-
"""
Параметры сервера
"""
import argparse
from openre.agent.helpers import mixin_log_level

parser = argparse.ArgumentParser(description='OpenRE.Agent server')
parser.add_argument(
    'type',
    help=argparse.SUPPRESS
)
parser.add_argument(
    'action',
    help='start/stop/restart'
)
parser.add_argument(
    '--pid',
    dest='pid_file',
    default=None,
    help='path to pid file (default: none)'
)

parser.add_argument(
    '--host',
    dest='host',
    default='*',
    help='host to listen for clients requests (default: *)'
)

parser.add_argument(
    '--port',
    dest='port',
    default='8932',
    help='port to listen for clients requests (default: 8932)'
)

parser.add_argument(
    '--proxy-host',
    dest='proxy_host',
    default='*',
    help='host to listen for domains data pub proxy (default: *)'
)

parser.add_argument(
    '--proxy-port',
    dest='proxy_port',
    default='8934',
    help='port to listen for domains data pub proxy (default: 8934)'
)

mixin_log_level(parser)
