# -*- coding: utf-8 -*-
"""
Содержит в себе информацию о доменах, запускаемых в других процессах / на других
серверах.
"""
from openre.helpers import StatsMixin
import logging

class RemoteDomain(StatsMixin):
    """
    Прокси к удаленному домену.
    """
    # FIXME: optimize send_synapse (collect portion of data and send it in one
    # request)
    def __init__(self, config, ore, domain_index):
        super(RemoteDomain, self).__init__()
        self.config = config
        self.ore = ore
        self.name = self.config['name']
        logging.debug('Create remote domain (name: %s)', config['name'])
        self.transport = None
        self.index = domain_index

    def __setattr__(self, name, value):
        print "%s = %s" % (name, value)
        super(RemoteDomain, self).__setattr__(name, value)

    def __getattr__(self, name):
        def api_call(*args, **kwargs):
            if name != 'send_synapse':
                print "%s(*%s, **%s)" % (name, args, kwargs)
            return
        return api_call

def test_remote_domain():
    from openre import OpenRE
    from openre.domain import Domain
    config = {
        'layers': [
            {
                'name': 'V1',
                'threshold': 30000,
                'relaxation': 1000,
                'width': 30,
                'height': 30,
                'connect': [
                    {
                        'name': 'V2',
                        'radius': 3,
                    },
                ],
            },
            {
                'name': 'V2',
                'threshold': 30000,
                'width': 10,
                'height': 10,
                'connect': [
                    {
                        'name': 'V2',
                        'radius': 3,
                    },
                ],
            },
        ],
        'domains': [
            {
                'name'        : 'D1',
                'layers'    : [
                    {'name': 'V1'},
                ],
            },
            {
                'name'        : 'D2',
                'layers'    : [
                    {'name': 'V2'},
                ],
            },
        ],
    }
    ore = OpenRE(config, local_domains=['D1'])
    local = ore.domains[0]
    remote = ore.domains[1]
    assert local.name == 'D1'
    assert local.index == 0
    assert isinstance(local, Domain)

    assert remote.name == 'D2'
    assert remote.index == 1
    assert isinstance(remote, RemoteDomain)
