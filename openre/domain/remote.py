# -*- coding: utf-8 -*-
"""
Содержит в себе информацию о доменах, запускаемых в других процессах / на других
серверах.
"""
from openre.domain.base import DomainBase
import logging
from openre.helpers import StatsMixin
from openre.layer import RemoteLayer
from copy import deepcopy

class RemoteDomainBase(DomainBase):
    def __init__(self, *args, **kwargs):
        super(RemoteDomainBase, self).__init__(*args, **kwargs)
        self.layers = []
        # domain layers config
        self.layers_config = deepcopy(self.config['layers'])

    def deploy_layers(self):
        """
        Create layers
        """
        logging.debug('Deploy domain (name: %s)', self.name)
        for layer_config in self.layers_config:
            layer = RemoteLayer(layer_config)
            self.layers.append(layer)
            layer_config['layer'] = layer
        for layer_config in self.layers_config:
            for connect in layer_config.get('connect', []):
                connect['domain_layers'] = []
            for layer in self.layers:
                for connect in layer_config.get('connect', []):
                    if connect['name'] == layer.name:
                        connect['domain_layers'].append(layer)

    def deploy_neurons(self):
        pass

    def pre_deploy_synapses(self):
        pass

    def deploy_synapses(self):
        pass

    def post_deploy_synapses(self):
        pass

    def deploy_indexes(self):
        pass

    def deploy_device(self):
        pass

    def create_synapses(self):
        pass

    def connect_layers(self):
        pass

    def create_neurons(self):
        pass

    def connect_neurons(self, pre_address, post_address, synapse_address):
        pass

    def send_spikes(self):
        pass

    def receive_spikes(self):
        pass

    def register_spike(self, receiver_neuron_index):
        pass

    def tick(self):
        pass

class RemoteDomainDummy(StatsMixin):
    """
    Do nothing
    """
    def __init__(self, *args, **kwargs):
        super(RemoteDomainDummy, self).__init__()

    def __getattr__(self, name):
        def api_call(*args, **kwargs):
            pass
        return api_call

def test_remote_domain():
    from openre import OpenRE
    from openre.domain import create_domain_factory, Domain
    class RemoteDomainTest(StatsMixin):
        """
        Тестовый прокси к удаленному домену.
        """
        def __init__(self, config, net, domain_index):
            super(RemoteDomainTest, self).__init__()
            self.config = config
            self.net = net
            self.name = self.config['name']
            logging.debug('Create remote domain (name: %s)', config['name'])
            self.index = domain_index

        def __setattr__(self, name, value):
            super(RemoteDomainTest, self).__setattr__(name, value)

        def __getattr__(self, name):
            def api_call(*args, **kwargs):
                self.stat_inc(name)
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
    local = ore.domains[0]
    remote = ore.domains[1]
    # 4 neurons in V1 connects to 4 neurons in V2 with radius 2
    assert remote.stat('send_synapse') == 4*4

    dummy = RemoteDomainDummy({'name':'D'}, None, 0)
    assert dummy.deploy_layers() is None
