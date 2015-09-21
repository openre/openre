# -*- coding: utf-8 -*-
"""
Индексы для быстрого поиска, например, всех синапсов нейрона.
"""
from openre.vector import Vector
from openre.metadata import ExtendableMetadata
from openre.data_types import types, null

class TransmitterIndex(object):
    """
    Индекс передающих нейронов
    i = 0..количество IS_TRANSMITTER нейронов
    j = 0..количество IS_RECEIVER нейронов
    local_address[i] - адрес IS_TRANSMITTER нейрона в domain.neurons
    flags[i] - текущие флаги IS_TRANSMITTER нейрона (их мы будем полчать из
        устройства)
    key[i] - адрес первого элемента в цепочке value[j]
    value[j] - следующий адрес IS_RECEIVER нейрона в удаленном домене или null
        если адрес последний
    remote_domain[j] - домен IS_RECEIVER нейрона
    remote_address[j] - адрес IS_RECEIVER нейрона в удаленнном домене
    """
    def __init__(self, data):
        self.local_address = Vector()
        meta_local_address = ExtendableMetadata((0, 1), types.address)
        self.local_address.add(meta_local_address)
        self.flags = Vector()
        meta_flags = ExtendableMetadata((0, 1), types.neuron_flags)
        self.flags.add(meta_flags)
        self.key = Vector()
        meta_key = ExtendableMetadata((0, 1), types.address)
        self.key.add(meta_key)

        self.value = Vector()
        meta_value = ExtendableMetadata((0, 1), types.address)
        self.value.add(meta_value)
        self.remote_domain = Vector()
        meta_remote_domain = ExtendableMetadata((0, 1), types.medium_address)
        self.remote_domain.add(meta_remote_domain)
        self.remote_address = Vector()
        meta_remote_address = ExtendableMetadata((0, 1), types.address)
        self.remote_address.add(meta_remote_address)

        value_index = -1
        for key_index, local_address in enumerate(data.keys()):
            meta_key[key_index] = null
            meta_flags[key_index] = 0
            meta_local_address[key_index] = local_address
            for domain_index in data[local_address]:
                value_index += 1
                prev_value_index = meta_key[key_index]
                meta_key[key_index] = value_index
                meta_value[value_index] = prev_value_index
                meta_remote_domain[value_index] = domain_index
                meta_remote_address[value_index] \
                        = data[local_address][domain_index]

        for vector in [self.local_address, self.flags, self.key,
                       self.value, self.remote_domain, self.remote_address]:
            vector.shrink()

    def __getitem__(self, key):
        value_address = self.key[key]
        ret = []
        # possible infinite loop in malformed indexes
        while value_address != null:
            ret.append(value_address)
            value_address = self.value[value_address]
            if value_address == null:
                return ret
        return ret

    def create_device_data_pointer(self, device):
        """
        Создание указателей на данные на устройстве
        """
        self.key.create_device_data_pointer(device)
        self.value.create_device_data_pointer(device)

    def to_device(self, device):
        """
        Загрузка на устройство
        """
        self.local_address.to_device(device)
        self.flags.to_device(device)

    def from_device(self, device):
        """
        Выгрузка с устройства
        """
        self.local_address.from_device(device)
        self.flags.from_device(device)


def test_index():
    from openre.helpers import OrderedDict
    data = OrderedDict([
        (218, OrderedDict([(1, 10), (12, 20)])),
        (300, OrderedDict([(1, 12)])),
        (77, OrderedDict([(5, 12), (6, 13)])),
    ])
    index = TransmitterIndex(
        data
    )
    for vector in [index.local_address, index.flags, index.key]:
        assert len(vector) == 3
    for vector in [index.value, index.remote_domain, index.remote_address]:
        assert len(vector) == 5
    assert list(index.local_address.data) == [218, 300, 77]
    assert list(index.flags.data) == [0, 0, 0]
    assert list(index.key.data) == [1, 2, 4]
    assert list(index.value.data) == [null, 0, null, null, 3]
    assert list(index.remote_domain.data) == [1, 12, 1, 5, 6]
    assert list(index.remote_address.data) == [10, 20, 12, 12, 13]
