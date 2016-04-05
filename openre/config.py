# -*- coding: utf-8 -*-
"""
Config management tool
"""
from copy import deepcopy
import uuid
import os
from functools import partial
from openre.helpers import randshift, from_json, to_json, set_default
from openre import types
import logging

class Config(dict):
    def __init__(self, data=None):
        if data is None:
            data = {}
        super(Config, self).__init__(deepcopy(data))
        self.root_defaults()
        self.is_cortex = {}
        self.domain_by_name = {}
        self.layer_by_name = {}
        self.connect_queue = []
        if 'layers' not in self:
            self['layers'] = []
        if 'domains' not in self:
            self['domains'] = []
        for layer in self['layers']:
            self.validate_layer(layer)
            self.layer_by_name[layer['name']] = layer
            self.layer_defaults(layer)
        for domain in self['domains']:
            self.validate_domain(domain)
            self.domain_by_name[domain['name']] = domain
            self.domain_defaults(domain)
        self.resolve_queue()

    def clear(self):
        self.is_cortex = {}
        self.domain_by_name = {}
        self.layer_by_name = {}
        self.connect_queue = []
        super(Config, self).clear()


    def root_defaults(self):
        defaults = {
            'rate_limit': 1000,
            'synapse': {
                'max_level': 30000,
                'learn_rate': 10,
                'learn_threshold': 1000,
                'spike_learn_threshold': 0,
                'spike_forget_threshold': 0,
            },
            'layers': [{
                'threshold': 30000,
                'relaxation': 1000,
                'is_inhibitory': False,
                'spike_cost': 10, # we want one spike per 10 ticks
                'max_vitality': types.max(types.vitality),
                'connect': [{
                    'radius': 1,
                    'shift': [0, 0],
                }]
                # 'name': required,
                # 'width': required,
                # 'height': required,
            }],
            'domains': [{
                'stat_size': 1000,
                'device': {
                    'type': 'OpenCL',
                },
            }]
        }
        set_default(self, {'defaults': defaults})
        for key in ['layers', 'domains']:
            if key not in self['defaults']:
                self['defaults'][key] = deepcopy(defaults[key])
        set_default(self, self['defaults'])

    def domain_defaults(self, domain):
        domain_defaults = self['defaults']['domains'][0]
        set_default(domain, domain_defaults)
        for domain_layer in domain.get('layers', []):
            self.domain_layer_defaults(domain_layer)

    def layer_defaults(self, layer):
        layer_defaults = self['defaults']['layers'][0]
        set_default(layer, layer_defaults)

    def domain_layer_defaults(self, domain_layer):
        layer_name = domain_layer['name']
        layer = self.layer_by_name[layer_name]
        domain_layer['width'] = layer['width']
        domain_layer['height'] = layer['height']
        if 'shape' not in domain_layer:
            domain_layer['shape'] = [0, 0, domain_layer['width'],
                                     domain_layer['height']]
        else:
            shape = domain_layer['shape']
            if shape[0] >= domain_layer['width']:
                logging.warn('Layer %s with shape = %s, shape[0] >= width',
                             layer_name, shape)
                shape[0] = domain_layer['width']
            if shape[1] >= domain_layer['height']:
                logging.warn('Layer %s with shape = %s, shape[1] >= height',
                             layer_name, shape)
                shape[1] = domain_layer['height']
            if shape[0] < 0:
                logging.warn('Layer %s with shape = %s, shape[0] < 0',
                             layer_name, shape)
                shape[0] = 0
            if shape[1] < 0:
                logging.warn('Layer %s with shape = %s, shape[1] < 0',
                             layer_name, shape)
                shape[1] = 0
            if shape[2] > domain_layer['width'] - shape[0]:
                logging.warn(
                    'Layer %s with shape = %s, shape[2] > width - shape[0]',
                    layer_name, shape)
                shape[2] = domain_layer['width'] - shape[0]
            if shape[3] > domain_layer['height'] - shape[1]:
                logging.warn(
                    'Layer %s with shape = %s, shape[3] > width - shape[1]',
                    layer_name, shape)
                shape[3] = domain_layer['height'] - shape[1]

    def validate_domain(self, domain):
        """
        Check if new domain has valid structure
        """
        if 'name' not in domain:
            raise ValueError('No domain name in %s' % domain)
        name = domain['name']
        if name in self.domain_by_name:
            raise ValueError('Duplicate domain name "%s"' % name)

    def validate_layer(self, layer):
        """
        Check if new layer has valid structure
        """
        if 'name' not in layer:
            raise ValueError('No layer name in %s' % layer)
        name = layer['name']
        if name in self.layer_by_name:
            raise ValueError('Duplicate layer name "%s"' % name)
        if 'width' not in layer:
            raise ValueError('No width in layer "%s"' % name)
        if 'height' not in layer:
            raise ValueError('No height in layer "%s"' % name)

    def make_unique(self):
        """
        Добавляет уникальный id для доменов. Необходим при создании новых
        agent.domain.
        Проверяет имя домена на наличие и на уникальность.
        """
        was_name = {}
        for domain_index, domain_config in enumerate(self.get('domains', [])):
            if 'name' not in domain_config:
                raise ValueError(
                    'No name for domain with index %s in config["domains"]' %
                    domain_index)
            name = domain_config['name']
            if name in was_name:
                raise ValueError(
                    'Domain name "%s" already was in domain with index %s' %
                    (name, was_name[name])
                )

            was_name[name] = domain_index
            if 'id' not in domain_config:
                domain_config['id'] = uuid.uuid4()
        return self

    def create_session(self, file_name):
        session = deepcopy(self)
        if os.path.isfile(file_name):
            session.load(file_name)
        else:
            session.save(file_name)
        session.make_unique()
        return session

    def delete_session(self, file_name):
        if os.path.isfile(file_name):
            os.remove(file_name)

    def save(self, file_name):
        with open(file_name, 'w') as out:
            out.write(to_json(self))

    def load(self, file_name):
        with open(file_name, 'r') as inp:
            self.clear()
            data = from_json(inp.read())
            self.update(data)

    def update(self, data):
        """
        Update config state
        """
        super(Config, self).update(data)

    def domain(self, name, width=None, height=None, device=None, type=None,
               input=None, output=None):
        if name in self.domain_by_name:
            return self.domain_by_name[name]
        if device is None and type is None:
            type = 'OpenCL'
        if device is None:
            device = {
                'type': type,
            }
        else:
            if 'type' not in device:
                device['type'] = 'OpenCL'
            if type is not None:
                device['type'] = type
        if device['type'] == 'OpenCL':
            device['threshold_inc'] = 10
            device['threshold_dec'] = 1
        self.domain_by_name[name] = {
            'name': name,
            'device': device,
        }
        self.domain_defaults(self.domain_by_name[name])
        if width:
            self.domain_by_name[name]['device']['width'] = width
        if height:
            self.domain_by_name[name]['device']['height'] = height
        if input:
            if isinstance(input, (list, tuple)):
                self.domain_by_name[name]['device']['input'] = input
            else:
                self.domain_by_name[name]['device']['input'] = [{"name": input}]
        if output:
            if isinstance(output, (list, tuple)):
                self.domain_by_name[name]['device']['output'] = output
            else:
                self.domain_by_name[name]['device']['output'] = [
                    {"name": output}
                ]
        self['domains'].append(self.domain_by_name[name])
        return self.domain_by_name[name]

    def layer(self, name, width, height, domain, connect=None,
              input=None, output=None):
        assert name not in self.layer_by_name
        assert domain in self.domain_by_name, \
            'Create domain "%s" first' % domain
        layer = {
            'name': name,
            'width': width,
            'height': height,
        }
        self.layer_defaults(layer)
        self.layer_by_name[name] = layer
        self['layers'].append(layer)
        if connect:
            layer['connect'] = []
            for layer_name in connect:
                self.connect_queue.append((layer_name, layer['connect']))
        domain = self.domain(domain)
        if 'layers' not in domain:
            domain['layers'] = []
        domain_layer = {
            'name': name,
        }
        if input:
            domain_layer['input'] = input
        if output:
            domain_layer['output'] = output
        domain['layers'].append(domain_layer)
        self.resolve_queue()

    def cortex(self, name, width, height, domain, connect=None,
               input=None, output=None):
        self.layer('%s_result' % name, width, height, domain, connect,
                   output=output)
        self.layer(
            '%s_excitatory' % name, width*2, height*2, domain,
            connect=[
            {
                'name': '%s_result' % name,
            },
            {
                'name': '%s_excitatory' % name,
                'radius': 4,
            },
            ], input=input)
        self.layer(
            '%s_inhibitory' % name, width*2, height*2, domain,
            connect=[{
                "name": '%s_excitatory' % name,
                "radius": 4,
                "shift": [
                    partial(randshift, 8, 20),
                    partial(randshift, 8, 20)
                ]
            }]
        )
        self.is_cortex[name] = True
        self.resolve_queue()

    def resolve_queue(self):
        connect_queue = self.connect_queue
        self.connect_queue = []
        for layer_name, connect in connect_queue:
            if isinstance(layer_name, dict):
                layer = layer_name
                layer_name = layer['name']
            else:
                layer = {
                    "name": layer_name,
                    "radius": 4,
                }
            # is cortex -> layer_name is virtual layer
            if layer_name in self.is_cortex:
                assert '%s_excitatory' % layer_name in self.layer_by_name
                assert '%s_inhibitory' % layer_name in self.layer_by_name
                assert '%s_result' % layer_name in self.layer_by_name
                sublayer = deepcopy(layer)
                sublayer.update({
                    "name": '%s_excitatory' % layer_name,
                })
                sublayer['radius'] = sublayer['radius'] * 2
                connect.append(sublayer)
                sublayer = deepcopy(layer)
                sublayer.update({
                    "name": '%s_inhibitory' % layer_name,
                })
                connect.append(sublayer)
            # ordinary layer
            elif layer_name in self.layer_by_name:
                connect.append(layer)
            # not found
            else:
                self.connect_queue.append((layer_name, connect))


def test_make_unique():
    from pytest import raises
    with raises(ValueError):
        Config({
            "layers"    : [
                {"name": "V1", "width": 1, "height": 1},
                {"name": "V2", "width": 1, "height": 1},
            ],
            "domains": [
                {
                    "layers"    : [
                        {"name": "V1"},
                        {"name": "V2"}
                    ]
                },
            ]
        }).make_unique()
    with raises(ValueError):
        Config({
            "layers"    : [
                {"name": "V1", "width": 1, "height": 1},
                {"name": "V3", "width": 1, "height": 1},
            ],
            "domains": [
                {
                    "name"        : "D2",
                    "layers"    : [
                        {"name": "V1"},
                    ]
                },
                {
                    "name"        : "D2",
                    "layers"    : [
                        {"name": "V3"}
                    ]
                }
            ]
        }).make_unique()
    config = {
        "layers"    : [
            {"name": "V1", "width": 1, "height": 1},
            {"name": "V3", "width": 1, "height": 1},
        ],
        "domains": [
            {
                "name"        : "D1",
                "layers"    : [
                    {"name": "V1"},
                ]
            },
            {
                "name"        : "D2",
                "layers"    : [
                    {"name": "V3"}
                ]
            }
        ]
    }
    config = Config(config).make_unique()
    assert config['domains'][0]['id']
    assert config['domains'][1]['id']

def test_config():
    from pytest import raises
    # Duplicate domain name
    with raises(ValueError):
        Config({"domains": [{"name" : "D1",}, {"name" : "D1"},]})
    with raises(ValueError):
        Config({"layers": [{"name" : "L1", "width":1, "height":1},
                           {"name" : "L1", "width":1, "height":1},]})
    config = Config({
        "domains": [{"name" : "D1",}, {"name" : "D2", "stat_size":1337},],
        "layers": [{"name" : "L1", "width":1, "height":1},
                   {"name" : "L2", "width":1, "height":1, "spike_cost": 20},],
    })
    assert 'D1' in config.domain_by_name
    assert config.domain_by_name['D1']['device']['type'] == 'OpenCL'
    domain_defaults = config['defaults']['domains'][0]
    layer_defaults = config['defaults']['layers'][0]
    assert config.domain_by_name['D1']['stat_size'] \
            == domain_defaults['stat_size']
    assert config.domain_by_name['D2']['stat_size'] == 1337
    assert config.layer_by_name['L1']['spike_cost'] \
            == layer_defaults['spike_cost']
    assert config.layer_by_name['L2']['spike_cost'] == 20
    assert 'D2' in config.domain_by_name
    assert 'L1' in config.layer_by_name
    assert 'L2' in config.layer_by_name

    with raises(AssertionError):
        config.layer('L2', 10, 10, 'D2')
    with raises(AssertionError):
        config.layer('L3', 10, 10, 'D3')
    config.domain('D3')
    config.layer('L3', 10, 20, 'D3')
    assert config.domain_by_name['D3']['device']['type'] == 'OpenCL'
    assert config.layer_by_name['L3']['is_inhibitory'] is False
