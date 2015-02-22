# -*- coding: utf-8 -*-
"""
Содержит в себе 2d массив однотипных нейронов.
"""
import logging
from openre.neurons import NeuronsMetadata, IS_INHIBITORY
from copy import deepcopy
import random
from openre.metadata import Metadata
from openre.vector import Vector
from openre.data_types import types


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
        layer_address: types.medium_address - номер слоя в domain.layers.
        address: types.address - aдрес первого элемента в векторе нейронов.
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
               которая будет моделироваться в данном слое. Задается в виде
               (y, x, height, width)
        """
        logging.debug('Create layer (id: %s)', config['id'])
        config = deepcopy(config)
        self.config = config
        self.id = self.config['id']
        # metadata for current layer (threshold, relaxation, etc.)
        self.layer_metadata = LayersMetadata(1)
        self.address = None
        self.threshold = self.config['threshold']
        self.is_inhibitory = self.config.get('is_inhibitory', False)
        self.relaxation = self.config.get('relaxation', 0)
        self.total_spikes = 0
        self.shape = self.config.get(
            'shape', [0, 0, self.config['width'], self.config['height']])
        if self.shape[0] >= self.config['width']:
            self.shape[0] = self.config['width']
        if self.shape[1] >= self.config['height']:
            self.shape[1] = self.config['height']
        if self.shape[0] < 0:
            self.shape[0] = 0
        if self.shape[1] < 0:
            self.shape[1] = 0
        if self.shape[2] > self.config['width'] - self.shape[0]:
            self.shape[2] = self.config['width'] - self.shape[0]
        if self.shape[3] > self.config['height'] - self.shape[1]:
            self.shape[3] = self.config['height'] - self.shape[1]
        self.x = self.shape[0]
        self.y = self.shape[1]
        self.width = self.shape[2]
        self.height = self.shape[3]
        if self.width == 0 or self.height == 0:
            logging.warn('Layer zero width or height, shape = %s', self.shape)
        self.length = self.width * self.height
        # metadata for current layer neurons
        self.neurons_metadata = NeuronsMetadata(self)

    def __repr__(self):
        return 'Layer(%s)' % repr(self.config)

    def __len__(self):
        return self.length

    def create_neurons(self):
        """
        Создание нейронов слоя в ранее выделенном для этого векторе
        """
        for i in xrange(self.length):
            self.neurons_metadata.level[i] \
                    = int(random.random() * (self.threshold + 1))
            self.neurons_metadata.flags[i] = 0
            if self.is_inhibitory:
                self.neurons_metadata.flags[i] |= IS_INHIBITORY
            self.neurons_metadata.layer[i] = self.layer_metadata.address

class LayersVector(object):
    """
    Вектор слоев домена
    """

    def __init__(self):
        self.threshold = Vector(types.threshold)
        self.relaxation = Vector(types.threshold)
        self.total_spikes = Vector(types.tick)
        self.length = 0

    def add(self, metadata):
        """
        Добавляем метаданные слоев в вектор
        """
        self.threshold.add(metadata.threshold)
        self.relaxation.add(metadata.relaxation)
        self.total_spikes.add(metadata.total_spikes)
        metadata.address = metadata.threshold.address
        self.length = self.threshold.length

    def __len__(self):
        return self.length

    def create(self):
        """
        Выделяем в памяти буфер под данные
        """
        self.threshold.create()
        self.relaxation.create()
        self.total_spikes.create()

    def create_device_data_pointer(self, device):
        """
        Создание указателей на данные на устройстве
        """
        self.threshold.create_device_data_pointer(device)
        self.relaxation.create_device_data_pointer(device)
        self.total_spikes.create_device_data_pointer(device)

    def to_device(self, device):
        """
        Загрузка на устройство
        """
        self.threshold.to_device(device)
        self.relaxation.to_device(device)
        self.total_spikes.to_device(device)

    def from_device(self, device):
        """
        Выгрузка с устройства
        """
        self.threshold.from_device(device)
        self.relaxation.from_device(device)
        self.total_spikes.from_device(device)


class LayersMetadata(object):
    """
    Метаданные для слоев
    """

    def __init__(self, length):
        self.threshold = Metadata((length, 1), types.threshold)
        self.relaxation = Metadata((length, 1), types.threshold)
        self.total_spikes = Metadata((length, 1), types.tick)
        self.address = None


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
        'shape': [0, 0, 30, 10],
    }
    config.update(layer_config)
    layer = Layer(config)
    assert layer.id == config['id']
    assert layer.address == None
    assert layer.threshold == config['threshold']
    assert layer.relaxation == config['relaxation']
    assert layer.total_spikes == 0
    assert layer.shape == [0, 0, 20, 10]
    assert layer.width == 20
    assert layer.height == 10
    assert layer.length == 200
    assert len(layer) == 200

    repr_layer = eval(repr(layer))
    assert repr_layer.id == layer.id

    config = {
        'id': 'V1',
    }
    config.update(layer_config)
    layer = Layer(config)
    assert layer.shape == [0, 0, 20, 20]
    assert layer.width == 20
    assert layer.height == 20
    assert layer.length == 400

