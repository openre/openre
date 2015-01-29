# -*- coding: utf-8 -*-
"""
Содержит в себе 2d массив однотипных нейронов.
"""
import logging

class Layer(object):
    """
    Слой (Layer) - набор однотипных нейронов, организованных в двухмерный
    массив.  Количество рядов и столбцов может быть разным, слой не обязательно
    квадратный. Размер разных слоев в одном домене может быть разным.
    """
    def __init__(self, config):
        """
        id: basestring, int или long - идентификатор слоя. Используется для
            возможности ссылаться на слои из доменов (в конфиге).
        address: types.address - уникальный внутри одного домена.
                 Принимает участие в формировании адреса нейрона.
        threshold: types.threshold - если neuron.level больше layer.threshold,
                   то происходит спайк. Не должен быть больше чем максимум у
                   синапса.
        relaxation: types.sinapse_level - на сколько снижается neuron.level
                    с каждым тиком (tick). По умолчанию - 0.
        total_spikes: types.address - количество спайков в слое за последний
                      тик.
        width: types.address - количество колонок в массиве нейронов
        height: types.address - количество рядов в массиве нейронов
        shape: types.shape - координаты и размер области (в исходном слое)
               которая будет моделироваться в данном слое.
        """
        logging.debug('Create layer (id: %s)', config['id'])
        self.config = config
        self.id = self.config['id']
        self.address = self.config['address']
        self.threshold = self.config['threshold']
        self.relaxation = self.config.get('relaxation', 0)
        self.total_spikes = 0
        self.shape = self.config.get(
            'shape', [0, 0, self.config['width'], self.config['height']])
        if self.shape[2] > self.config['width']:
            self.shape[2] = self.config['width']
        if self.shape[2] > self.config['height']:
            self.shape[2] = self.config['height']
        self.width = self.shape[2]
        self.height = self.shape[3]
        self.length = self.width * self.height

    def __len__(self):
        return self.length


def test_layer():
    layer_config = {
        'id': 'V1',
        'threshold': 30000,
        'relaxation': 1000,
        'width': 20,
        'height': 20,
    }
    config = {
        'id': 'V1',
        'address': 0,
        'shape': [0, 0, 30, 10],
    }
    config.update(layer_config)
    layer = Layer(config)
    assert layer.id == config['id']
    assert layer.address == config['address']
    assert layer.threshold == config['threshold']
    assert layer.relaxation == config['relaxation']
    assert layer.total_spikes == 0
    assert layer.shape == [0, 0, 20, 10]
    assert layer.width == 20
    assert layer.height == 10
    assert layer.length == 200
    assert len(layer) == 200

    config = {
        'id': 'V1',
        'address': 0,
    }
    config.update(layer_config)
    layer = Layer(config)
    assert layer.shape == [0, 0, 20, 20]
    assert layer.width == 20
    assert layer.height == 20
    assert layer.length == 400

