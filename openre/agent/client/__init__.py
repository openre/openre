# -*- coding: utf-8 -*-
"""
Клиентская часть агента.
"""
from openre.agent.client.args import parser
from openre.agent.client.client import Agent
from openre.agent.args import parse_args

def run():
    args = parse_args(parser)
    agent = Agent(vars(args))
    agent.run()

