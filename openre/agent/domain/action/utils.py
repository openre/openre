# -*- coding: utf-8 -*-

from openre.agent.decorators import action
import time

@action()
def ping(agent):
    return 'pong'

@action()
def exception(agent):
    raise Exception('Test exception')

@action()
def check_args(agent, *args, **kwargs):
    return {'args': args, 'kwargs': kwargs}

@action()
def domain_proxy(agent, message, domain_index):
    return domain_index

@action()
def sleep(agent, timeout=10):
    time.sleep(timeout)
    return timeout


