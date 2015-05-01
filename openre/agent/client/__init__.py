# -*- coding: utf-8 -*-
"""
Серверная часть агента. Запускается на сервере, открывает соединение для
получения команд из клиентской части.
"""
from openre.agent.helpers import parse_args
from openre.agent.client.args import parser
from openre.agent.client import client

def run():
    args = parse_args(parser)

    if args.action == 'hello':
        client.hello(args)

