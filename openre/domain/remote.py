# -*- coding: utf-8 -*-
"""
Содержит в себе информацию о доменах, запускаемых в других процессах / на других
серверах.
"""
from openre.helpers import StatsMixin
import logging

class RemoteDomainBase(StatsMixin):
    def __init__(self, config, net, domain_index):
        super(RemoteDomainBase, self).__init__()
        self.config = config
        self.net = net
        self.name = self.config['name']
        logging.debug('Create remote domain (name: %s)', config['name'])
        self.index = domain_index

    def __getattr__(self, name):
        raise NotImplementedError

class RemoteDomainDummy(RemoteDomainBase):
    """
    Do nothing
    """
    # FIXME: optimize send_synapse (collect portion of data and send it in one
    # request)
    def __getattr__(self, name):
        def api_call(*args, **kwargs):
            pass
        return api_call

def test_remote_domain():
    from openre import OpenRE
    from openre.domain import create_domain_factory, Domain
    class RemoteDomainTest(RemoteDomainBase):
        """
        Тестовый прокси к удаленному домену.
        """
        def __setattr__(self, name, value):
            print "%s = %s" % (name, value)
            super(RemoteDomainTest, self).__setattr__(name, value)

        def __getattr__(self, name):
            def api_call(*args, **kwargs):
                self.stat_inc(name)
                if name != 'send_synapse':
                    print "%s(*%s, **%s)" % (name, args, kwargs)
                return
            return api_call

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
    ore = OpenRE(config)
    ore.deploy(create_domain_factory(Domain, RemoteDomainTest, ['D1']))
    local = ore.domains[0]
    remote = ore.domains[1]
    assert local.name == 'D1'
    assert local.index == 0
    assert isinstance(local, Domain)

    assert remote.name == 'D2'
    assert remote.index == 1
    assert isinstance(remote, RemoteDomainTest)
    assert remote.stat('send_synapse') == 17424
    assert remote.stat('deploy_layers') == 1
    assert remote.stat('deploy_neurons') == 1
    assert remote.stat('pre_deploy_synapses') == 1
    assert remote.stat('deploy_indexes') == 1
    assert remote.stat('deploy_device') == 1

    config = {
        'layers': [
            {
                'name': 'V1',
                'threshold': 30000,
                'relaxation': 1000,
                'width': 2,
                'height': 2,
                'connect': [
                    {
                        'name': 'V2',
                        'radius': 2,
                    },
                ],
            },
            {
                'name': 'V2',
                'threshold': 30000,
                'width': 2,
                'height': 2,
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
    ore = OpenRE(config)
    ore.deploy(create_domain_factory(Domain, RemoteDomainTest, ['D1']))
    remote = ore.domains[1]
    # 4 neurons in V1 connects to 4 neurons in V2 with radius 2
    assert remote.stat('send_synapse') == 4*4

