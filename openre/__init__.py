# -*- coding: utf-8 -*-
from openre.domain import Domain
from copy import deepcopy
from time import time
import logging

__version__ = '0.0.1'

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
        if 'sinapse' not in self.config:
            self.config['sinapse'] = {}
        if 'max_level' not in self.config['sinapse']:
            self.config['sinapse']['max_level'] = 30000
        for layer in self.config['layers']:
            if 'threshold' not in layer:
                layer['threshold'] = self.config['sinapse']['max_level']
            if 'is_inhibitory' not in layer:
                layer['is_inhibitory'] = False
            layer_by_id[layer['id']] = layer

        # TODO: - выдавать предупреждение если не весь слой моделируется
        #       - выдавать предупреждение или падать если один и тот же слoй
        #           частично или полностью моделируется дважды
        for domain in self.config['domains']:
            domain = deepcopy(domain)
            if 'device' not in domain:
                domain['device'] = {
                    'type': 'OpenCL'
                }
            for domain_layer in domain['layers']:
                domain_layer.update(deepcopy(layer_by_id[domain_layer['id']]))
            self.domains.append(Domain(domain, self))

    def run(self):
        """
        Основной цикл.
        """
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
            if 'shape' in row:
                shape = row['shape']
                # coordinate is out of domains layer bounds
                if x < shape[0] \
                   or x >= shape[0] + shape[2] \
                   or y < shape[1] \
                   or y >= shape[1] + shape[3] \
                   or x < 0 or y < 0 \
                   or x >= row['width'] or y >= row['height']:
                    continue
            else:
                if x < 0 or y < 0 \
                   or x >= row['width'] or y >= row['height']:
                    continue
            return {
                'domain_id': row['domain_id'],
                'layer_index': row['layer_index'],
            }
        return None


def test_openre():
    from openre.neurons import IS_INHIBITORY
    from openre.data_types import null
    from openre.device import OpenCL
    sinapse_max_level = 30000
    config = {
        'sinapse': {
            'max_level': sinapse_max_level
        },
        'layers': [
            {
                'id': 'V1',
                'threshold': sinapse_max_level,
                'relaxation': 1000,
                'width': 20,
                'height': 20,
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
                'width': 5,
                'height': 10,
            },
            {
                'id': 'V4',
                'width': 5,
                'height': 10,
            },
        ],
        'domains': [
            {
                'id'        : 'D1',
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
                'layers'    : [
                    {'id': 'V1', 'shape': [10, 10, 10, 10]},
                    {'id': 'V1', 'shape': [0, 10, 10, 10]},
                    {'id': 'V3', 'shape': [-1, -1, 20, 20]},
                ],
            },
            {
                'id'        : 'D3',
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
    # domain layers
    assert isinstance(ore.domains[0].device, OpenCL)
    assert ore.domains[0].layers[0].id == 'V1'
    assert ore.domains[0].layers_config[0]['layer'].id == 'V1'
    assert ore.domains[0] \
            .layers_config[0]['connect'][0]['domain_layers'][0].id == 'V2'
    assert ore.domains[0].layers[1].address == 100
    assert ore.domains[0].layers[2].address == 200
    assert not ore.domains[0].layers[0].metadata.flags[0] & IS_INHIBITORY
    assert not ore.domains[0].layers[1].metadata.flags[0] & IS_INHIBITORY
    assert ore.domains[0].layers[2].metadata.flags[0] & IS_INHIBITORY
    # neurons
    assert ore.domains[0].neurons.length == 300
    assert ore.domains[0].neurons.length == len(ore.domains[0].neurons)
    assert ore.domains[1].neurons.length == 250
    # sinapses
    assert ore.domains[0].sinapses
    assert ore.domains[0].sinapses.length
    assert ore.domains[0].sinapses.length == \
            ore.domains[0].sinapses.level.length
    assert ore.domains[0].sinapses.length == \
            len(ore.domains[0].sinapses.level.data)
    assert len(ore.domains[0].pre_sinapse_index.value.data) \
            == len(ore.domains[0].sinapses)
    assert len(ore.domains[0].pre_sinapse_index.key.data) \
            == len(ore.domains[0].neurons)
    assert len([x for x in ore.domains[0].pre_sinapse_index.value.data
                if x != null]) == 0
    assert len([x for x in ore.domains[0].post_sinapse_index.value.data
                if x != null]) == 150
    assert len([x for x in ore.domains[0].pre_sinapse_index.key.data
                if x != null]) == 200
    assert len([x for x in ore.domains[0].post_sinapse_index.key.data
                if x != null]) == 50
    # check layer shape
    assert ore.domains[1].layers[2].shape == [0, 0, 5, 10]
    assert ore.domains[2].layers[0].shape == [4, 4, 1, 6]
    assert ore.domains[2].layers[1].shape == [5, 10, 0, 0]


    for i, domain_config in enumerate(config['domains']):
        domain = ore.domains[i]
        assert domain.id == domain_config['id']
        assert domain.learn_threshold == \
                domain_config.get('learn_threshold', 0)
        assert domain.forget_threshold == \
                domain_config.get('forget_threshold', 0)
        assert domain.ticks == 0
        for j, layer_config in enumerate(domain.config['layers']):
            layer = domain.layers[j]
            assert layer.id == layer_config['id']
            assert layer.address == layer.metadata.address
            assert layer.threshold == layer_config['threshold']
            assert layer.relaxation == \
                    layer_config.get('relaxation', 0)
            assert layer.metadata
        domain.tick()
        assert domain.ticks == 1

