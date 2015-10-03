# -*- coding: utf-8 -*-

from openre.agent.decorators import action

@action(namespace='server')
def ping(event):
    return 'pong'

@action(namespace='server')
def exception(event):
    raise Exception('Test exception')

@action(namespace='server')
def check_args(event, *args, **kwargs):
    return {'args': args, 'kwargs': kwargs}

