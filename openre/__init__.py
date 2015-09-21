# -*- coding: utf-8 -*-
from openre.domain import Domain
from copy import deepcopy
from time import time
import logging
from openre.data_types import types
import os.path

__version__ = '0.0.1'
BASE_PATH = os.path.dirname(os.path.realpath(__file__))

class OpenRE(object):
    """
    Основной класс. Пример работы:
        from openre import OpenRE
        ore = OpenRE(config)
        ore.run()
    config - содержит в себе настройки для домена включая оборудование, на
             котором будут проходить вычисления.
    Пример config:
        {
            'domain': {
                'id'        : 1,
                'device'    : '0',
                'layers'    : [
                    {
                        'threshold': 30000,
                        'relaxation': 1000,
                    },
                    {
                        'threshold': 30000,
                    }
                ],
            },
        }
    """
    def __init__(self, config):
        self.config = deepcopy(config)
        self.domains = []
        self._find = None
        self.deploy()

    def __repr__(self):
        return 'OpenRE(%s)' % repr(self.config)

    def deploy(self):
        """
        Создание домена.
        """
        layer_by_id = {}
        if 'synapse' not in self.config:
            self.config['synapse'] = {}
        if 'max_level' not in self.config['synapse']:
            self.config['synapse']['max_level'] = 30000
        if 'learn_rate' not in self.config['synapse']:
            self.config['synapse']['learn_rate'] = 10
        if 'learn_threshold' not in self.config['synapse']:
            self.config['synapse']['learn_threshold'] = 9000
        if 'spike_learn_threshold' not in self.config['synapse']:
            self.config['synapse']['spike_learn_threshold'] = 0
        if 'spike_forget_threshold' not in self.config['synapse']:
            self.config['synapse']['spike_forget_threshold'] = 0
        for layer in self.config['layers']:
            if 'threshold' not in layer:
                layer['threshold'] = self.config['synapse']['max_level']
            if 'is_inhibitory' not in layer:
                layer['is_inhibitory'] = False
            if 'spike_cost' not in layer:
                # target is one spike per 10 ticks
                layer['spike_cost'] = 10
            if 'max_vitality' not in layer:
                layer['max_vitality'] = types.max(types.vitality)
            layer_by_id[layer['id']] = layer

        # TODO: - выдавать предупреждение если не весь слой моделируется
        #       - выдавать предупреждение или падать если один и тот же слoй
        #           частично или полностью моделируется дважды
        domain_index = -1
        for domain in self.config['domains']:
            domain_index += 1
            domain = deepcopy(domain)
            if 'device' not in domain:
                domain['device'] = {
                    'type': 'OpenCL'
                }
            if 'stat_size' not in domain:
                # how many ticks collect stats before get them from device
                domain['stat_size'] = 1000
            for domain_layer in domain['layers']:
                domain_layer.update(deepcopy(layer_by_id[domain_layer['id']]))
            domain = Domain(domain, self)
            domain.index = domain_index
            self.domains.append(domain)
        for domain in self.domains:
            domain.deploy_layers()
        for domain in self.domains:
            domain.deploy_neurons()
            domain.pre_deploy_synapses()
        # here wait for all domains is synced
        for domain in self.domains:
            domain.deploy_synapses()
        # here wait for all domains is synced
        for domain in self.domains:
            domain.post_deploy_synapses()
            domain.deploy_indexes()
            domain.deploy_device()

    def run(self):
        """
        Основной цикл.
        """
        logging.debug('Run')
        last_sec = int(time())
        tick_per_sec = 0
        logger_level = logging.getLogger().getEffectiveLevel()
        while True:
            if logger_level <= logging.DEBUG:
                now = int(time())
                if last_sec != now:
                    last_sec = now
                    logging.debug('Ticks/sec: %s', tick_per_sec)
                    tick_per_sec = 0
                tick_per_sec += 1
            for domain in self.domains:
                domain.tick()

    def find(self, layer_id, x, y):
        """
        Ищет домен и слой для заданных координат x и y в слое layer_id
        """
        # precache
        if self._find is None:
            self._find = {}
            layer_by_id = {}
            for layer in self.config['layers']:
                layer_by_id[layer['id']] = layer

            for domain in self.config['domains']:
                domain_id = domain['id']
                layer_index = -1
                for layer in domain['layers']:
                    layer = deepcopy(layer)
                    layer_index += 1
                    domain_layer_id = layer['id']
                    if domain_layer_id not in self._find:
                        self._find[domain_layer_id] = []
                    layer['domain_id'] = domain_id
                    layer['layer_index'] = layer_index
                    layer['width'] = layer_by_id[domain_layer_id]['width']
                    layer['height'] = layer_by_id[domain_layer_id]['height']
                    self._find[domain_layer_id].append(layer)
        if layer_id not in self._find:
            return None
        for row in self._find[layer_id]:
            if 'shape' not in row:
                if x < 0 or y < 0 \
                   or x >= row['width'] or y >= row['height']:
                    continue
            else:
                shape = row['shape']
                # coordinate is out of domains layer bounds
                if x < shape[0] \
                   or x >= shape[0] + shape[2] \
                   or y < shape[1] \
                   or y >= shape[1] + shape[3] \
                   or x < 0 or y < 0 \
                   or x >= row['width'] or y >= row['height']:
                    continue
            return {
                'domain_id': row['domain_id'],
                'layer_index': row['layer_index'],
            }
        return None


def test_openre():
    from openre.neurons import IS_INHIBITORY, IS_TRANSMITTER, IS_RECEIVER
    from openre.data_types import null
    from openre.device import Dummy
    from pytest import raises
    synapse_max_level = 30000
    config = {
        'synapse': {
            'max_level': synapse_max_level,
            'learn_rate': 10,
            'learn_threshold': 9000,
            'spike_learn_threshold': 0,
            'spike_forget_threshold': 0,
        },
        'layers': [
            {
                'id': 'V1',
                'threshold': 20000,
                'relaxation': 1000,
                'width': 20,
                'height': 20,
                'spike_cost': 11,
                'max_vitality': types.max(types.vitality) - 1,
                'connect': [
                    {
                        'id': 'V2',
                        'radius': 1,
                        'shift': [0, 0],
                    },
                ],
            },
            {
                'id': 'V2',
                'threshold': 10000,
                'relaxation': 2000,
                'width': 10,
                'height': 10,
                'is_inhibitory': True,
                'connect': [
                    {
                        'id': 'V3',
                        'radius': 1,
                        'shift': [-1, 1],
                    },
                ],
            },
            {
                'id': 'V3',
                'threshold': 15000,
                'relaxation': 3000,
                'width': 5,
                'height': 10,
                'connect': [
                    {
                        'id': 'V4',
                        'radius': 2,
                        'shift': [0, 0],
                    },
                ],
            },
            {
                'id': 'V4',
                'threshold': 25000,
                'relaxation': 4000,
                'width': 5,
                'height': 10,
            },
        ],
        'domains': [
            {
                'id'        : 'D1',
                'device': {'type': 'Dummy'},
                'layers'    : [
                    # 'shape': [x, y, width, height]
                    {'id': 'V1', 'shape': [0, 0, 10, 10]},
                    {'id': 'V1', 'shape': [10, 0, 10, 10]},
                    # если параметр shape не указан - подразумеваем весь слой
                    {'id': 'V2'},
                ],
            },
            {
                'id'        : 'D2',
                'device': {'type': 'Dummy'},
                'layers'    : [
                    {'id': 'V1', 'shape': [10, 10, 10, 10]},
                    {'id': 'V1', 'shape': [0, 10, 10, 10]},
                    {'id': 'V3', 'shape': [-1, -1, 20, 20]},
                ],
            },
            {
                'id'        : 'D3',
                'device': {'type': 'Dummy'},
                'layers'    : [
                    {'id': 'V4', 'shape': [4, 4, 20, 20]},
                    {'id': 'V4', 'shape': [5, 10, 20, 20]},
                ],
            },
        ],
    }
    ore = OpenRE(config)
    assert ore
    assert ore.find('V2', 0, 10) == None
    assert ore.find('V1', 0, 20) == None
    assert ore.find('V1', 1, 1) == {
        'domain_id': 'D1',
        'layer_index': 0
    }
    assert ore.find('V1', 1, 11) == {
        'domain_id': 'D2',
        'layer_index': 1
    }
    assert ore.domains[0].index == 0
    # domain layers
    assert isinstance(ore.domains[0].device, Dummy)
    assert ore.domains[0].config['stat_size'] == 1000
    # 200 synapses in domain D1
    assert len(ore.domains[0].stat.data) \
            == ore.domains[0].stat_fields
    assert ore.domains[0].layers[0].id == 'V1'
    assert ore.domains[0].layers_config[0]['layer'].id == 'V1'
    assert ore.domains[0] \
            .layers_config[0]['connect'][0]['domain_layers'][0].id == 'V2'
    assert ore.domains[0].layers[1].address == 100
    assert ore.domains[0].layers[2].address == 200
    assert not ore.domains[0].layers[0].neurons_metadata.flags[0] \
            & IS_INHIBITORY
    assert not ore.domains[0].layers[1].neurons_metadata.flags[0] \
            & IS_INHIBITORY
    assert ore.domains[0].layers[2].neurons_metadata.flags[0] & IS_INHIBITORY
    assert list(ore.domains[0].layers_vector.threshold.data) \
            == [20000, 20000, 10000]
    assert list(ore.domains[1].layers_vector.threshold.data) \
            == [20000, 20000, 15000]
    assert list(ore.domains[2].layers_vector.threshold.data) == [25000, 25000]
    assert list(ore.domains[0].layers_vector.relaxation.data) \
            == [1000, 1000, 2000]
    assert list(ore.domains[1].layers_vector.relaxation.data) \
            == [1000, 1000, 3000]
    assert list(ore.domains[2].layers_vector.relaxation.data) == [4000, 4000]
    assert list(ore.domains[0].layers_vector.spike_cost.data) == [11, 11, 10]
    max_vitality = types.max(types.vitality)
    assert list(ore.domains[0].layers_vector.max_vitality.data) \
            == [max_vitality - 1, max_vitality - 1, max_vitality]
    # neurons
    assert ore.domains[0].neurons.length == 300 + 200 # 200 - remote neurons
    assert ore.domains[0].neurons.length == len(ore.domains[0].neurons)
    assert ore.domains[0].neurons.vitality[0] == max_vitality - 1
    assert ore.domains[0].neurons.vitality[100] == max_vitality - 1
    assert ore.domains[0].neurons.vitality[200] == max_vitality
    assert ore.domains[1].neurons.length == 250 + 72 # 72 remote neurons
    neuron_layers_0 = [0]*100
    neuron_layers_0.extend([1]*100)
    neuron_layers_0.extend([2]*100)
    # remote neurons
    neuron_layers_0.extend([0]*100)
    neuron_layers_0.extend([1]*100)
    assert list(ore.domains[0].neurons.layer.data) == neuron_layers_0
    # synapses
    assert ore.domains[0].synapses
    assert ore.domains[0].synapses.length
    assert ore.domains[0].synapses.length == \
            ore.domains[0].synapses.level.length
    assert ore.domains[0].synapses.length == \
            len(ore.domains[0].synapses.level.data)
    assert len(ore.domains[0].pre_synapse_index.value.data) \
            == len(ore.domains[0].synapses)
    assert len(ore.domains[0].pre_synapse_index.key.data) \
            == len(ore.domains[0].neurons)
    # every pre neuron has only one synapse
    assert len([x for x in ore.domains[0].pre_synapse_index.value.data
                if x != null]) == 0
    # every neuron in V2 has 4 connections from V1 layer
    # -> 3/4 has valid address
    assert len([x for x in ore.domains[0].post_synapse_index.value.data
                if x != null]) == 150 + 150 # second one is remote neurons
    # number of connected pre neurons
    assert len([x for x in ore.domains[0].pre_synapse_index.key.data
                if x != null]) == 200 + 200 # second one is remote neurons
    # number of connected post neurons
    assert len([x for x in ore.domains[0].post_synapse_index.key.data
                if x != null]) == 50 + 50 # second one connections from remote
                                          # neurons
    # check layer shape
    assert ore.domains[1].layers[2].shape == [0, 0, 5, 10]
    assert ore.domains[2].layers[0].shape == [4, 4, 1, 6]
    assert ore.domains[2].layers[1].shape == [5, 10, 0, 0]

    # multy domains
    d1 = ore.domains[0]
    d2 = ore.domains[1]
    d3 = ore.domains[2]
    v2 = d1.layers[2]
    assert not v2.neurons_metadata.flags[0] & IS_TRANSMITTER
    assert v2.neurons_metadata.flags[2, 0] & IS_TRANSMITTER
    assert d1.remote_neurons_metadata.flags[199] & IS_RECEIVER
    assert len(d2.remote_neurons_metadata.level) == 72
    with raises(IndexError):
        d1.remote_neurons_metadata.flags[200]
    assert d1.remote_neurons_metadata.vitality[0] \
            == types.max(types.vitality) - 1
    assert d2.remote_neurons_metadata.vitality[0] & IS_INHIBITORY
    assert not d1.remote_neurons_metadata.vitality[0] & IS_INHIBITORY
    # remote neuron in d2 (domain index == 1)
    # to local neuron in d3->remote_neurons
    assert d3.remote_to_local_neuron_address[1][218] == 6
    # local neuron #218 in d2 to remote neuron #6 in d3 (domain index == 2)
    assert d2.local_to_remote_neuron_address[218][2] == 6
    assert d2.neurons.flags.data[218] & IS_TRANSMITTER
    assert d3.neurons.flags.data[6] & IS_RECEIVER
    assert len(d2.transmitter_index.key.data) == 207
    assert len(d2.transmitter_index.value.data) == 207


    for i, domain_config in enumerate(config['domains']):
        domain = ore.domains[i]
        assert domain.id == domain_config['id']
        assert domain.spike_learn_threshold == \
                ore.config['synapse']['spike_learn_threshold']
        assert domain.spike_forget_threshold == \
                ore.config['synapse']['spike_forget_threshold']
        assert domain.learn_rate == \
                ore.config['synapse']['learn_rate']
        assert domain.learn_threshold == \
                ore.config['synapse']['learn_threshold']
        assert domain.ticks == 0
        for j, layer_config in enumerate(domain.config['layers']):
            layer = domain.layers[j]
            assert layer.id == layer_config['id']
            assert layer.address == layer.neurons_metadata.address
            assert layer.threshold == layer_config['threshold']
            assert layer.relaxation == \
                    layer_config.get('relaxation', 0)
            assert layer.neurons_metadata
        domain.tick()
        assert domain.ticks == 1

