# -*- coding: utf-8 -*-
"""
Работа с коммандной строкой
"""
import argparse

parser = argparse.ArgumentParser(
    description='Console utilites',
    add_help=False
)
parser.add_argument(
    'type',
    metavar='server|client|proxy',
    help='type of the agent'
)

