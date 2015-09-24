# -*- coding: utf-8 -*-
"""
Параметры клиента
"""
import argparse
from openre.agent.args import mixin_log_level, mixin_default
#import sys

parser = argparse.ArgumentParser(description='OpenRE.Agent client')

mixin_default(parser)

parser.add_argument(
    'action',
    help='command to send'
)

parser.add_argument(
    '--data',
    default='null',
    help='data to send, json or string'
)

parser.add_argument(
    '--host',
    dest='host',
    default='localhost',
    help='host of the server (default: localhost)'
)

parser.add_argument(
    '--port',
    dest='port',
    default='8932',
    help='port of the server (default: 8932)'
)

parser.add_argument(
    '--pretty',
    dest='pretty',
    action='store_true',
    help='pretty print the result'
)

parser.add_argument(
    '--config',
    dest='config',
#    nargs='?',
    type=argparse.FileType('r'),
#    default=sys.stdin,
    help='config json file for net'
)


mixin_log_level(parser)

