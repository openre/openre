# -*- coding: utf-8 -*-
"""
Индексы для быстрого поиска, например, всех синапсов нейрона.
"""
from openre.vector import Vector
from openre.metadata import Metadata
from openre.data_types import types, null

class Index(object):
    """
    Создает индекс для поиска всех self.value[j] для каждого self.key[i].
    self.key - вектор ключей
    self.value - вектор значений
    j = self.key[i]
    next_j = self.value[j]
    Если next_j == data_types.null, то value[j] - последний элемент в цепочке.
    """
    def __init__(self, length, data):
        self.key = Vector()
        self.value = Vector()
        meta_key = Metadata((length, 1), types.address)
        meta_value = Metadata((len(data), 1), types.address)
        self.key.add(meta_key)
        self.key.fill(null)
        self.value.add(meta_value)
        self.value.fill(null)
        for value_address, key_address in enumerate(data):
            prev_value_address = self.key.data[key_address]
            self.key.data[key_address] = value_address
            self.value.data[value_address] = prev_value_address

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
        self.key.to_device(device)
        self.value.to_device(device)

    def from_device(self, device):
        """
        Выгрузка с устройства
        """
        self.key.from_device(device)
        self.value.from_device(device)


def test_index():
    from pytest import raises
    data = [0, 0, 2, 2, 5, 5, 3, 0, 4, 4, 4, 4, 1]
    index = Index(
        10,
        data
    )
    assert index.key[9] == null
    assert len(index.key) == 10
    assert len(index.value) == len(data)
    assert list(index.value.data) \
            == [null, 0, null, 2, null, 4, null, 1, null, 8, 9, 10, null]
    assert list(index.key.data) == [7, 12, 3, 6, 11, 5, null, null, null, null]
    assert index[0] == [7, 1, 0]
    assert index[4] == [11, 10, 9, 8]
    assert index[9] == []
    with raises(IndexError):
        index[10]

