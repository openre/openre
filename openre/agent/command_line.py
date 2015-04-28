# -*- coding: utf-8 -*-
"""
Работа с коммандной строкой
"""
import argparse

parser = argparse.ArgumentParser(description='Domain manager')
parser.add_argument(
    'action',
    help='start/stop/restart'
)
parser.add_argument(
    '--pid',
    dest='pid_file',
    default='./ore-agent.pid',
    help='path to pid file (default: ./ore-agent.pid)'
)
