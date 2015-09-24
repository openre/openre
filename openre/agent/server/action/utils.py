# -*- coding: utf-8 -*-

from openre.agent.decorators import action

@action()
def ping(event):
    return 'pong'

@action()
def exception(event):
    raise Exception('Test exception')

@action()
def check_args(event, *args, **kwargs):
    return {'args': args, 'kwargs': kwargs}

