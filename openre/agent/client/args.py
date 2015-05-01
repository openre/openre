# -*- coding: utf-8 -*-
"""
Параметры клиента
"""
import argparse
from openre.agent.helpers import mixin_log_level

parser = argparse.ArgumentParser(description='OpenRE.Agent client')
parser.add_argument(
    'type',
    help='client'
)
parser.add_argument(
    'action',
    help='hello'
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

mixin_log_level(parser)

