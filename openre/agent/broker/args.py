# -*- coding: utf-8 -*-
"""
Параметры сервера
"""
import argparse
from openre.agent.args import mixin_log_level, mixin_default

parser = argparse.ArgumentParser(description='OpenRE.Agent proxy')

mixin_default(parser)

parser.add_argument(
    'action',
    help='start/stop/restart'
)

parser.add_argument(
    '--host',
    dest='host',
    default='*',
    help='host to listen for domains pub proxy (default: *)'
)

parser.add_argument(
    '--port',
    dest='port',
    default='8934',
    help='port to listen for domains pub proxy (default: 8934)'
)

mixin_log_level(parser)
