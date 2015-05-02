# -*- coding: utf-8 -*-
"""
Серверная часть агента. Запускается на сервере, открывает соединение для
получения команд из клиентской части.
"""
from openre.agent.client.args import parser
from openre.agent.client.client import Agent
from openre.agent.args import parse_args

def run():
    args = parse_args(parser)
    agent =Agent(args)
    agent.run()

