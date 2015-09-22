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
    def __init__(self, data=None):
        self.local_address = Vector()
        self.meta_local_address = ExtendableMetadata((0, 1), types.address)
        self.local_address.add(self.meta_local_address)
        self.flags = Vector()
        self.meta_flags = ExtendableMetadata((0, 1), types.neuron_flags)
        self.flags.add(self.meta_flags)
        self.key = Vector()
        self.meta_key = ExtendableMetadata((0, 1), types.address)
        self.key.add(self.meta_key)

        self.value = Vector()
        self.meta_value = ExtendableMetadata((0, 1), types.address)
        self.value.add(self.meta_value)
        self.remote_domain = Vector()
        self.meta_remote_domain \
                = ExtendableMetadata((0, 1), types.medium_address)
        self.remote_domain.add(self.meta_remote_domain)
        self.remote_address = Vector()
        self.meta_remote_address = ExtendableMetadata((0, 1), types.address)
        self.remote_address.add(self.meta_remote_address)

        self.data = {}
        self.address_to_key_index = {}
        self.key_pos = -1
        self.value_pos = -1
        if data:
            self.rebuild(data)

    def add(self, local_address, remote_domain_index, remote_address):
        """
        Добавляет один элемент в индекс
        """
        if local_address in self.data \
           and remote_domain_index in self.data[local_address]:
            return
        key_index = self.address_to_key_index.get(local_address)
        if key_index is None:
            self.key_pos += 1
            self.data[local_address] = {}
            self.address_to_key_index[local_address] = self.key_pos
            key_index = self.key_pos

            self.meta_key[key_index] = null
            self.meta_flags[key_index] = 0
            self.meta_local_address[key_index] = local_address
        self.value_pos += 1
        value_index = self.value_pos
        prev_value_index = self.meta_key[key_index]
        self.meta_key[key_index] = value_index
        self.meta_value[value_index] = prev_value_index
        self.meta_remote_domain[value_index] = remote_domain_index
        self.meta_remote_address[value_index] = remote_address

        self.data[local_address][remote_domain_index] = remote_address

    def rebuild(self, data):
        """
        Перестраивает весь индекс
        """
        # TODO: do not loose order in self.data

        self.data = {}
        self.key_pos = -1
        self.value_pos = -1
        self.address_to_key_index = {}
        for local_address in data.keys():
            for domain_index in data[local_address]:
                self.add(local_address,
                         domain_index, data[local_address][domain_index])
        self.shrink()

    def shrink(self):
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
        self.local_address.create_device_data_pointer(device)
        self.flags.create_device_data_pointer(device)

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
    index2 = TransmitterIndex()
    for local_address in data.keys():
        for domain_index in data[local_address].keys():
            index2.add(local_address,
                       domain_index, data[local_address][domain_index])
    index2.shrink()
    assert list(index.local_address.data) == list(index2.local_address.data)
    assert list(index.flags.data) == list(index2.flags.data)
    assert list(index.key.data) == list(index2.key.data)
    assert list(index.value.data) == list(index2.value.data)
    assert list(index.remote_domain.data) == list(index2.remote_domain.data)
    assert list(index.remote_address.data) == list(index2.remote_address.data)

