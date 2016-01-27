# -*- coding: utf-8 -*-

from openre.agent.decorators import action
import logging

@action(namespace='server')
def ping(event):
    return 'pong'

@action(namespace='server')
def exception(event):
    raise Exception('Test exception')

@action(namespace='server')
def check_args(event, *args, **kwargs):
    return {'args': args, 'kwargs': kwargs}

@action(namespace='server')
def debug(event):
    logging.debug('Debug message: %s', event.data['message'])

@action(namespace='server')
def error(event):
    logging.debug('Error message: %s', event.data['message'])

@action(namespace='server')
def warn(event):
    logging.warn('Warn message: %s', event.data['message'])
