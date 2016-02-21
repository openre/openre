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
    data[i] - результат перевода спайков в число. Если спайка небыло - число
        уменьшается на 1 пока не станет равным нулю. Если спайк был, смотрим
        разницу между текущим тиком домена и предыдущим в tick[i] и переводим
        разницу в число
    tick[i] - тик при котором был предыдущий спайк нейрона.
    """
    def __init__(self):
        self.address = Vector()
        self.meta_address = ExtendableMetadata((0, 1), types.address)
        self.address.add(self.meta_address)

        self.data = Vector()
        self.meta_data = ExtendableMetadata((0, 1), types.output)
        self.data.add(self.meta_data)

        self.tick = Vector()
        self.meta_tick = ExtendableMetadata((0, 1), types.tick)
        self.tick.add(self.meta_tick)

        self.pos = -1

    def add(self, layer):
        """
        Добавляет все нейроны из layer в индекс
        """
        if not layer.config.get('output'):
            return
        neurons_metadata = layer.neurons_metadata
        neurons_metadata_address = neurons_metadata.address
        for i in xrange(len(layer)):
            self.pos += 1
            index = self.pos
            self.meta_address[index] = neurons_metadata_address + i
            self.meta_data[index] = 0
            self.meta_tick[index] = 0

    def clear(self):
        self.pos = -1
        for meta in [self.meta_address, self.meta_data, self.meta_tick]:
            meta.resize(length=0)

    def shrink(self):
        for vector in [self.address, self.data, self.tick]:
            vector.shrink()

    def create_device_data_pointer(self, device):
        """
        Создание указателей на данные на устройстве
        """
        self.address.create_device_data_pointer(device)
        self.data.create_device_data_pointer(device)
        self.tick.create_device_data_pointer(device)

    def to_device(self, device):
        """
        Загрузка на устройство
        """
        self.address.to_device(device)
        self.data.to_device(device)
        self.tick.to_device(device)

    def from_device(self, device):
        """
        Выгрузка с устройства
        """
        self.address.from_device(device)
        self.data.from_device(device)
        self.tick.from_device(device)



def test_output_index():
    index = OutputIndex()

    from openre import OpenRE
    from openre import neurons
    config = {
        'layers': [
            {
                'name': 'V1',
                'width': 16,
                'height': 10,
                'threshold': 255,
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
    D1.neurons.level.data[:] = 0
    device1 = ore.domains[0].device
    for layer in D1.layers:
        index.add(layer)
    index.shrink()
    assert len(index.address.data) == 80
    assert len(index.data.data) == len(index.address.data)
    assert len(index.tick.data) == len(index.address.data)
    assert index.data.data.dtype.type == types.output
    assert list(index.address.data) \
            == range(40) + [80 + x for x in range(40)]
    assert list(D1.output_index.address.data) == list(index.address.data)
    assert len(D1.output_index.address.data) == len(index.address.data)
    for _ in xrange(255):
        num = -1
        for layer in D1.layers:
            for i in xrange(len(layer.neurons_metadata.level)):
                num += 1
                layer.neurons_metadata.level[i] += num
        D1.neurons.level.to_device(device1)
        ore.tick()
        D1.neurons.level.from_device(device1)
        D1.neurons.flags.from_device(device1)
        oi = D1.output_index
        oi.data.from_device(device1)
        oi.tick.from_device(device1)
        for index, neuron_address in enumerate(oi.address.data):
            if D1.neurons.flags[neuron_address] & neurons.IS_SPIKED:
                assert oi.tick[index] == D1.ticks
        assert oi.tick[0] == 0
        print D1.output_index.data.data
    assert list(D1.output_index.data.data) == \
       [  0,   1,   1, 171, 129, 205, 173, 186, 193, 204, 209, 217, 221, 221, 229, 239, 225, 241,
        241, 239, 235, 235, 241, 241, 243, 243, 241, 241, 241, 244, 244, 244, 241, 241, 241, 241,
        241, 246, 246, 246, 249, 249, 249, 249, 249, 253, 253, 253, 253, 253, 253, 253, 253, 253,
        253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253,
        253, 253, 253, 253, 253, 253, 253, 253,]
