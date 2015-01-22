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
        self.domain = None
        self.deploy()

    def deploy(self):
        """
        Создание домена.
        """
        self.domain = Domain(self.config['domain'])

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
            self.domain.tick()

def test_openre():
    config = {
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
    ore = OpenRE(config)
    assert ore
    assert ore.domain.id == config['domain']['id']
    assert ore.domain.learn_threshold == \
            config['domain'].get('learn_threshold', 0)
    assert ore.domain.forget_threshold == \
            config['domain'].get('forget_threshold', 0)
    assert ore.domain.ticks == 0
    layer_id = -1
    for layer_config in config['domain']['layers']:
        layer_id += 1
        layer = ore.domain.layers[layer_id]
        assert layer.id == layer_id
        assert layer.threshold == layer_config['threshold']
        assert layer.relaxation == layer_config.get('relaxation', 0)
    ore.domain.tick()
    assert ore.domain.ticks == 1
