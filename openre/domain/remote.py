# -*- coding: utf-8 -*-
"""
Содержит в себе информацию о доменах, запускаемых в других процессах / на других
серверах.
"""
from openre.helpers import StatsMixin
import logging

class RemoteDomain(StatsMixin):
    def __init__(self, config, ore):
        super(RemoteDomain, self).__init__()
        logging.debug('Create remote domain (name: %s)', config['name'])

    def __getattr__(self, name): # FIXME: REMOVE THIS METHOD !!!!!!!!!!!!!!!
        def api_call(*args, **kwargs):
            return
        return api_call
