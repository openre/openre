# -*- coding: utf-8 -*-
"""
Индекс всех transmitter нейронов в домене и их адресов в других доменах
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
    is_spiked[i] - признак того, что нужно передать спайк, то же самое что и
        neuron.flags & IS_SPIKED && !(neuron.flags & IS_DEAD)
    key[i] - адрес первого элемента в цепочке value[j]
    value[j] - следующий адрес IS_RECEIVER нейрона в удаленном домене или null
        если адрес последний
    remote_domain[j] - домен IS_RECEIVER нейрона
    remote_address[j] - адрес IS_RECEIVER нейрона в удаленнном домене
    remote_receiver_index[j] - адрес IS_RECEIVER нейрона в
        post_domain.receive_index
    """
    def __init__(self, data=None):
        self.local_address = Vector()
        self.meta_local_address = ExtendableMetadata((0, 1), types.address)
        self.local_address.add(self.meta_local_address)
        self.is_spiked = Vector()
        self.meta_is_spiked = ExtendableMetadata((0, 1), types.neuron_flags)
        self.is_spiked.add(self.meta_is_spiked)
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
        self.remote_receiver_index = Vector()
        self.meta_remote_receiver_index \
                = ExtendableMetadata((0, 1), types.address)
        self.remote_receiver_index.add(self.meta_remote_receiver_index)

        self.data = {}
        self.address_to_key_index = {}
        self.key_pos = -1
        self.value_pos = -1
        if data:
            self.rebuild(data)

    def add(self, local_address, remote_domain_index, remote_address,
            remote_receiver_index):
        """
        Добавляет один элемент в индекс
        """
        if local_address in self.data \
           and remote_domain_index in self.data[local_address]:
            return False
        key_index = self.address_to_key_index.get(local_address)
        if key_index is None:
            self.key_pos += 1
            self.data[local_address] = {}
            self.address_to_key_index[local_address] = self.key_pos
            key_index = self.key_pos

            self.meta_key[key_index] = null
            self.meta_is_spiked[key_index] = 0
            self.meta_local_address[key_index] = local_address
        self.value_pos += 1
        value_index = self.value_pos
        prev_value_index = self.meta_key[key_index]
        self.meta_key[key_index] = value_index
        self.meta_value[value_index] = prev_value_index
        self.meta_remote_domain[value_index] = remote_domain_index
        self.meta_remote_address[value_index] = remote_address
        self.meta_remote_receiver_index[value_index] = remote_receiver_index

        self.data[local_address][remote_domain_index] = (remote_address,
                                                        remote_receiver_index)
        return True

    def clear(self):
        self.data = {}
        self.key_pos = -1
        self.value_pos = -1
        self.address_to_key_index = {}
        for meta in [self.meta_local_address,
                     self.meta_is_spiked, self.meta_key,
                     self.meta_value, self.meta_remote_domain,
                     self.meta_remote_address]:
            meta.resize(length=0)

    def rebuild(self, data):
        """
        Перестраивает весь индекс
        """
        # TODO: do not loose order in self.data

        self.clear()
        for local_address in data.keys():
            for domain_index in data[local_address]:
                remote_address, remote_receiver_index \
                        = data[local_address][domain_index]
                self.add(local_address,
                         domain_index, remote_address, remote_receiver_index)
        self.shrink()

    def shrink(self):
        for vector in [self.local_address, self.is_spiked,
                       self.key, self.value, self.remote_domain,
                       self.remote_address, self.remote_receiver_index]:
            vector.shrink()

    def create_device_data_pointer(self, device):
        """
        Создание указателей на данные на устройстве
        """
        self.local_address.create_device_data_pointer(device)
        self.is_spiked.create_device_data_pointer(device)

    def to_device(self, device):
        """
        Загрузка на устройство
        """
        self.local_address.to_device(device)
        self.is_spiked.to_device(device)

    def from_device(self, device):
        """
        Выгрузка с устройства
        """
        self.local_address.from_device(device)
        self.is_spiked.from_device(device)


def test_index():
    from openre.helpers import OrderedDict
    data = OrderedDict([
        (218, OrderedDict([(1, (10, 41)), (12, (20, 42))])),
        (300, OrderedDict([(1, (12, 43))])),
        (77, OrderedDict([(5, (12, 44)), (6, (13, 45))])),
    ])
    index = TransmitterIndex(
        data
    )
    for vector in [index.local_address, index.is_spiked,
                   index.key]:
        assert len(vector) == 3
    for vector in [index.value, index.remote_domain, index.remote_address,
                   index.remote_receiver_index]:
        assert len(vector) == 5
    assert index.key_pos == 2
    assert index.value_pos == 4
    assert list(index.local_address.data) == [218, 300, 77]
    assert list(index.is_spiked.data) == [0, 0, 0]
    assert list(index.key.data) == [1, 2, 4]
    assert list(index.value.data) == [null, 0, null, null, 3]
    assert list(index.remote_domain.data) == [1, 12, 1, 5, 6]
    assert list(index.remote_address.data) == [10, 20, 12, 12, 13]
    assert list(index.remote_receiver_index.data) == [41, 42, 43, 44, 45]
    assert index.address_to_key_index[218] == 0
    assert index.address_to_key_index[77] == 2

    # check add method
    index2 = TransmitterIndex()
    for local_address in data.keys():
        for domain_index in data[local_address].keys():
            remote_address, remote_receiver_index \
                    = data[local_address][domain_index]
            index2.add(local_address,
                       domain_index, remote_address, remote_receiver_index)
            # additional call should be ignored
            index2.add(local_address,
                       domain_index, remote_address, remote_receiver_index)
    index2.shrink()
    assert list(index.local_address.data) == list(index2.local_address.data)
    assert list(index.is_spiked.data) == list(index2.is_spiked.data)
    assert list(index.key.data) == list(index2.key.data)
    assert list(index.value.data) == list(index2.value.data)
    assert list(index.remote_domain.data) == list(index2.remote_domain.data)
    assert list(index.remote_address.data) == list(index2.remote_address.data)
    assert list(index.remote_receiver_index.data) \
            == list(index2.remote_receiver_index.data)

    # check rebuild
    data = OrderedDict([
        (77, OrderedDict([(5, (12, 44)), (6, (13, 45))])),
        (218, OrderedDict([(1, (10, 41)), (12, (20, 42))])),
    ])
    index2.rebuild(data)
    assert index2.key_pos == 1
    assert index2.value_pos == 3
    assert len(index2.key.data) == 2
    assert len(index2.value.data) == 4
    assert len(index2.meta_key) == 2
    assert len(index2.meta_value) == 4
