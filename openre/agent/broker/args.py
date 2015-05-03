# -*- coding: utf-8 -*-
"""
Параметры сервера
"""
import argparse
from openre.agent.args import mixin_log_level, mixin_default
from openre.agent.args import mixin_server_endpoint

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

mixin_log_level(parser)
mixin_server_endpoint(parser)
