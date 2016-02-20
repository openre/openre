# -*- coding: utf-8 -*-
"""
Индекс всех output нейронов в домене
"""
from openre.vector import Vector
from openre.metadata import ExtendableMetadata
from openre.data_types import types

class OutputIndex(object):
    """
    Индекс всех output нейронов. С помощью этого индекса генерится numpy массив
    в котором спайки переводятся в числа. Чем выше частота спайков у нейрона,
    тем больше будет число.
    i = 0..количество output нейронов
    address[i] - адрес output нейрона
    """
    def __init__(self):
        self.address = Vector()
        self.meta_address = ExtendableMetadata((0, 1), types.address)
        self.address.add(self.meta_address)

        self.data = Vector()
        self.meta_data = ExtendableMetadata((0, 1), types.output)
        self.data.add(self.meta_data)

        self.pos = -1

    def add(self, layer):
        """
        Добавляет все нейроны из layer в индекс
        """
        neurons_metadata = layer.neurons_metadata
        neurons_metadata_address = neurons_metadata.address
        for i in xrange(len(layer)):
            self.pos += 1
            index = self.pos
            self.meta_address[index] = neurons_metadata_address + i

    def clear(self):
        self.pos = -1
        for meta in [self.meta_address, self.meta_data]:
            meta.resize(length=0)

    def shrink(self):
        for vector in [self.address, self.data]:
            vector.shrink()

    def create_device_data_pointer(self, device):
        """
        Создание указателей на данные на устройстве
        """
        self.address.create_device_data_pointer(device)
        self.data.create_device_data_pointer(device)

    def to_device(self, device):
        """
        Загрузка на устройство
        """
        self.address.to_device(device)
        self.data.to_device(device)

    def from_device(self, device):
        """
        Выгрузка с устройства
        """
        self.address.from_device(device)
        self.data.from_device(device)




def test_output_index():
    index = OutputIndex()

    from openre import OpenRE
    config = {
        'layers': [
            {
                'name': 'V1',
                'width': 16,
                'height': 10,
            },
        ],
        'domains': [
            {
                'name'        : 'D1',
                'device'    : {
                    'type': 'OpenCL',
                },
                'layers'    : [
                    {'name': 'V1', 'output': 'o1', 'shape': [0, 0, 8, 5]},
                    {'name': 'V1', 'shape': [8, 0, 8, 5]},
                    {'name': 'V1', 'output': 'o3', 'shape': [0, 5, 8, 5]},
                    {'name': 'V1', 'shape': [8, 5, 8, 5]},
                ],
            },
        ],
    }
    ore = OpenRE(config)
    ore.deploy()
    D1 = ore.domains[0]
    assert len(index.address.data) == 0
    num = -1
    for layer in D1.layers:
        for i in xrange(len(layer.neurons_metadata.level)):
            num += 1
            layer.neurons_metadata.level[i] = num
        if layer.config.get('output'):
            index.add(layer)
    index.shrink()
    assert len(index.address.data) == 80
    assert index.data.data.dtype.type == types.output
    assert list(index.address.data) \
            == range(40) + [80 + x for x in range(40)]

