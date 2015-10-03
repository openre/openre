# -*- coding: utf-8 -*-

from openre.agent.decorators import action
import time

@action(namespace='domain')
def ping(event):
    return 'pong'

@action(namespace='domain')
def exception(event):
    raise Exception('Test exception')

@action(namespace='domain')
def check_args(event, *args, **kwargs):
    return {'args': args, 'kwargs': kwargs}

@action(namespace='domain')
def domain_proxy(event, message, domain_index):
    return domain_index

@action(namespace='domain')
def sleep(event, timeout=10):
    time.sleep(timeout)
    return timeout


