# -*- coding: utf-8 -*-

from openre.agent.decorators import action

@action()
def ping():
    return 'pong'

@action()
def exception():
    raise Exception('Test exception')

