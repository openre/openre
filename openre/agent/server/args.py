# -*- coding: utf-8 -*-
"""
Параметры сервера
"""
import argparse

parser = argparse.ArgumentParser(description='OpenRE.Agent server')
parser.add_argument(
    'type',
    help='server'
)
parser.add_argument(
    'action',
    help='start/stop/restart'
)
parser.add_argument(
    '--pid',
    dest='pid_file',
    default=None,
    help='path to pid file (default: ./ore-agent.pid)'
)
