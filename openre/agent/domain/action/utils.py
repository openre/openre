# -*- coding: utf-8 -*-

from openre.agent.decorators import action
import time

@action()
def ping(event):
    return 'pong'

@action()
def exception(event):
    raise Exception('Test exception')

@action()
def check_args(event, *args, **kwargs):
    return {'args': args, 'kwargs': kwargs}

@action()
def domain_proxy(event, message, domain_index):
    return domain_index

@action()
def sleep(event, timeout=10):
    time.sleep(timeout)
    return timeout


