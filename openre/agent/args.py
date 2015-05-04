# -*- coding: utf-8 -*-
"""
Работа с коммандной строкой
"""
import argparse
import logging
import uuid

parser = argparse.ArgumentParser(
    description='Console utilites',
    add_help=False
)
parser.add_argument(
    'type',
    metavar='server|client|proxy|broker|domain',
    help='type of the agent'
)

def mixin_default(parser):
    """
    Add default arguments such as type and id
    """
    parser.add_argument(
        'type',
        help=argparse.SUPPRESS
    )
    parser.add_argument(
        '--id',
        dest='id',
        type=uuid.UUID,
        help='UUID of the agent (default: uuid4())',
        default=uuid.uuid4()
    )


def mixin_log_level(parser):
    """
    Add --log-level argument in parser
    """
    def check_log_level(value):
        """
        Validate --log-level argument
        """
        if value not in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG',
                         'NOTSET']:
            raise argparse.ArgumentTypeError(
                "%s is an invalid log level value" % value)
        return value

    parser.add_argument(
        '--log-level',
        metavar='',
        type=check_log_level,
        dest='log_level',
        default=None,
        help='logging level, one of the: CRITICAL, ERROR, WARNING, INFO,' \
             ' DEBUG, NOTSET (default: none)'
    )

def mixin_server_endpoint(parser):
    """
    Add --server-host and --server-port arguments in parser
    """
    parser.add_argument(
        '--server-host',
        dest='server_host',
        default='127.0.0.1',
        help='host of the server to connect (default: 127.0.0.1)'
    )

    parser.add_argument(
        '--server-port',
        dest='server_port',
        default='8932',
        help='port of the server to connect (default: 8932)'
    )


def parse_args(parser, *args, **kwargs):
    args = parser.parse_args(*args, **kwargs)
    if hasattr(args, 'log_level') and args.log_level:
        logging.basicConfig(
            format='%(levelname)s: %(message)s',
            level=getattr(logging, args.log_level)
        )
    return args


