# -*- coding: utf-8 -*-
"""
Индекс всех receiver нейронов в домене
"""
from openre.vector import Vector
from openre.metadata import ExtendableMetadata
from openre.data_types import types

class ReceiverIndex(object):
    """
    Индекс принимающих нейронов
    i = 0..количество IS_RECEIVER нейронов
    i - адрес IS_RECEIVER нейрона в индексе (этот адрес приходит из других
        доменов)
    local_address[i] - адрес IS_RECEIVER нейрона в domain.neurons
    is_spiked[i] - информация о спайке IS_RECEIVER нейрона (ее мы будем полчать
        из IS_TRANSMITTER нейрона в другом домене)
    remote_domain[i] - домен IS_TRANSMITTER нейрона
    remote_address[i] - адрес IS_TRANSMITTER нейрона в удаленнном домене
    """
    def __init__(self, data=None):
        self.local_address = Vector()
        self.meta_local_address = ExtendableMetadata((0, 1), types.address)
        self.local_address.add(self.meta_local_address)
        self.is_spiked = Vector()
        self.meta_is_spiked = ExtendableMetadata((0, 1), types.neuron_flags)
        self.is_spiked.add(self.meta_is_spiked)
        self.meta_remote_domain \
                = ExtendableMetadata((0, 1), types.medium_address)
        self.remote_domain = Vector()
        self.remote_domain.add(self.meta_remote_domain)
        self.remote_address = Vector()
        self.meta_remote_address = ExtendableMetadata((0, 1), types.address)
        self.remote_address.add(self.meta_remote_address)
        self.data = {}
        self.address_to_index = {}
        self.pos = -1
        if data:
            self.rebuild(data)

    def add(self, local_address, remote_domain_index, remote_address):
        """
        Добавляет один элемент в индекс
        """
        # self.data[remote_domain_index][remote_address] = local_address
        if remote_domain_index in self.data \
           and remote_address in self.data[remote_domain_index]:
            return False
        index = self.address_to_index.get(local_address)
        if index:
            return False
        self.pos += 1
        if remote_domain_index not in self.data:
            self.data[remote_domain_index] = {}
        self.data[remote_domain_index][remote_address] = local_address
        self.address_to_index[local_address] = self.pos
        index = self.pos

        self.meta_is_spiked[index] = 0
        self.meta_local_address[index] = local_address
        self.meta_remote_domain[index] = remote_domain_index
        self.meta_remote_address[index] = remote_address

        return True

    def clear(self):
        self.data = {}
        self.pos = -1
        self.address_to_index = {}
        for meta in [self.meta_local_address, self.meta_is_spiked,
                     self.meta_remote_domain,
                     self.meta_remote_address]:
            meta.resize(length=0)

    def rebuild(self, data):
        """
        Перестраивает весь индекс
        """
        # TODO: do not loose order in self.data
        self.clear()
        for remote_domain_index in data.keys():
            for remote_address in data[remote_domain_index]:
                self.add(data[remote_domain_index][remote_address],
                         remote_domain_index, remote_address)
        self.shrink()

    def shrink(self):
        for vector in [self.local_address, self.is_spiked,
                       self.remote_domain, self.remote_address]:
            vector.shrink()

    def get_local_address(self, remote_domain_index, remote_address):
        """
        Получаем локальный адрес IS_RECEIVER нейрона по адресу IS_TRANSMITTER
        нейрона другого домена
        """
        if remote_domain_index not in self.data:
            return
        return self.data[remote_domain_index].get(remote_address)

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
        (1, OrderedDict([(100, 200), (120, 220)])),
        (2, OrderedDict([(111, 211)])),
        (3, OrderedDict([(122, 222), (126, 213), (126, 213)])),
    ])
    index = ReceiverIndex(
        data
    )
    for vector in [index.local_address, index.is_spiked, index.remote_domain,
                   index.remote_address]:
        assert len(vector) == 5
    assert index.pos == 4
    assert list(index.local_address.data) == [200, 220, 211, 222, 213]
    assert list(index.is_spiked.data) == [0, 0, 0, 0, 0]
    assert list(index.remote_domain.data) == [1, 1, 2, 3, 3]
    assert list(index.remote_address.data) == [100, 120, 111, 122, 126]
    assert index.address_to_index[200] == 0
    assert index.address_to_index[222] == 3
    assert index.get_local_address(2, 111) == 211
    assert index.get_local_address(2, 122) is None

    # check add method
    index2 = ReceiverIndex()
    for domain_index in data.keys():
        for remote_address in data[domain_index].keys():
            local_address = data[domain_index][remote_address]
            index2.add(local_address,
                       domain_index, remote_address)
            # additional call should be ignored
            index2.add(local_address,
                       domain_index, remote_address)
    index2.shrink()
    assert list(index.local_address.data) == list(index2.local_address.data)
    assert list(index.is_spiked.data) == list(index2.is_spiked.data)
    assert list(index.remote_domain.data) == list(index2.remote_domain.data)
    assert list(index.remote_address.data) == list(index2.remote_address.data)

    # check rebuild
    data = OrderedDict([
        (77, OrderedDict([(5, 12), (6, 13)])),
        (218, OrderedDict([(1, 10), (12, 20)])),
    ])
    index2.rebuild(data)
    assert index2.pos == 3
    assert len(index2.local_address.data) == 4
