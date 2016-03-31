# -*- coding: utf-8 -*-
"""
Клиентская часть агента.
"""
from openre.agent.client.args import parser
from openre.agent.client.client import Agent
from openre.agent.args import parse_args
from openre.agent.helpers import do_strict_action
from copy import deepcopy

def run():
    args = parse_args(parser)
    agent = Agent(vars(args))
    agent.run()

class Client(object):
    """
    Proxy to agent.client.action.* actions
    """
    def __init__(self, config, **kwargs):
        conf = deepcopy(kwargs)
        conf['config'] = config
        self.agent = Agent(conf)

    def __getattr__(self, name):
        def action(*args, **kwargs):
            return do_strict_action(name, 'client', self.agent, *args, **kwargs)
        return action

