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
        self.deploy()

    def deploy(self):
        """
        Создание домена.
        """
        layer_by_id = {}
        for layer in self.config['layers']:
            layer_by_id[layer['id']] = layer

        # TODO: - выдавать предупреждение если не весь слой моделируется
        #       - выдавать предупреждение или падать если один и тот же слoй
        #           частично или полностью моделируется дважды
        for domain in self.config['domains']:
            for domain_layer in domain['layers']:
                domain_layer.update(layer_by_id[domain_layer['id']])
            self.domains.append(Domain(domain))

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

def test_openre():
    config = {
        'layers': [
            {
                'id': 'V1',
                'threshold': 30000,
                'relaxation': 1000,
                'width': 20,
                'height': 20,
            },
            {
                'id': 'V2',
                'threshold': 30000,
                'width': 10,
                'height': 10,
            }
        ],
        'domains': [
            {
                'id'        : 'D1',
                'device'    : '0',
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
                'device'    : '0',
                'layers'    : [
                    {'id': 'V1', 'shape': [10, 10, 10, 10]},
                    {'id': 'V1', 'shape': [0, 10, 10, 10]},
                ],
            },
        ],
    }
    ore = OpenRE(config)
    assert ore
    assert ore.domains[0].layers[1].address == 100
    assert ore.domains[0].layers[2].address == 200
    assert ore.domains[0].neurons.length == 300
    assert ore.domains[0].neurons.length == len(ore.domains[0].neurons)
    assert ore.domains[1].neurons.length == 200
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

