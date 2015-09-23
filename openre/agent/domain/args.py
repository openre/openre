# -*- coding: utf-8 -*-
"""
Параметры домена
"""
import argparse
from openre.agent.args import mixin_log_level, mixin_server_endpoint
from openre.agent.args import mixin_default

parser = argparse.ArgumentParser(description='OpenRE.Agent proxy')

mixin_default(parser)

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
    '--name',
    default='domain',
    help='name of the domain. (default: domain)'
)

mixin_log_level(parser)
mixin_server_endpoint(parser)
