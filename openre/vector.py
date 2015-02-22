# -*- coding: utf-8 -*-
"""
Вектор
"""
import numpy as np
from openre.errors import OreError


class Vector(object):
    """
    Хранит в себе одномерный массив, который можно копировать на устройство
    и с устройства. Допускается создание вектора нулевой длины.
    """

    def __init__(self, type=None):
        self.length = 0
        self.metadata = []
        self.data = None
        self.device_data_pointer = None
        self.type = type

    def add(self, metadata):
        """
        Добавляет метаданные, по которым построит вектор, в metadata через
        set_address передает self и адрес первого элемента. Все метаданные
        должны быть одного типа.
        """
        if not self.metadata:
            self.type = metadata.type
        else:
            assert self.type == metadata.type
        if metadata.vector:
            raise OreError('Metadata already assigned to vector')
        address = self.length
        self.metadata.append(metadata)
        self.length += metadata.length
        metadata.set_address(self, address)

    def __len__(self):
        return self.length

    def create(self):
        """
        Создает в памяти вектор заданного типа и помещает его в self.data
        """
        assert self.data is None
        self.data = np.zeros((self.length)).astype(self.type)

    def create_device_data_pointer(self, device):
        """
        Создает self.device_data_pointer для устройства device
        """
        self.device_data_pointer = device.create(self.data)

    def to_device(self, device, is_blocking=True):
        """
        Копирует данные из self.data в устройство
        """
        device.upload(
            self.device_data_pointer, self.data, is_blocking=is_blocking)
        return self.device_data_pointer

    def from_device(self, device, is_blocking=True):
        """
        Копирует данные из устройства в self.data
        """
        device.download(
            self.data, self.device_data_pointer, is_blocking=is_blocking)
        return self.data

    def __getitem__(self, key):
        if key < 0 or key >= self.length:
            raise IndexError
        return self.data[key]

    def __setitem__(self, key, value):
        if key < 0 or key >= self.length:
            raise IndexError
        self.data[key] = value

    def fill(self, value):
        """
        Заполняет весь вектор значением value
        """
        return self.data.fill(value)

class RandomIntVector(Vector):
    """
    При создании указывается диапазон случайных значений, которыми будет
    заполнен RandomIntVector, в отличии от заполнении нулями в исходном Vector.
    """
    def create(self, low, high=None):
        """
        Создает в памяти вектор заданного типа и помещает его в self.data
        """
        assert self.data is None
        self.data = np.random.random_integers(
            low, high=high, size=(self.length)).astype(self.type)



def test_vector():
    from openre.metadata import Metadata
    from openre.data_types import types
    from pytest import raises

    meta0 = Metadata((10, 20), types.index_flags)
    meta1 = Metadata((25, 15), types.index_flags)
    assert meta0.address is None

    vector = Vector()
    assert vector.type is None
    vector.add(meta0)
    assert vector.type == meta0.type
    assert meta0.address == 0
    vector.add(meta1)
    assert vector.type == meta1.type
    assert meta1.address == 200 # 10*20 - shape of m0
    def has_2_metas():
        assert vector.length == 10*20 + 25*15
        assert vector.data == None
        assert len(vector.metadata) == 2
        assert vector.metadata[0] == meta0
    has_2_metas()

    if types.index_flags != types.tick:
        meta2 = Metadata((2, 3), types.tick)
        with raises(AssertionError):
            vector.add(meta2)
        has_2_metas()
    vector.create()
    assert len(vector.data) == 10*20 + 25*15
    assert np.result_type(vector.data) == vector.type
    with raises(AssertionError):
        vector.create()
    vector2 = Vector(types.index_flags)
    assert vector2.type == types.index_flags


    vector = Vector()
    meta3 = Metadata((0, 0), types.index_flags)
    with raises(OreError):
        vector.add(meta0)
    vector.add(meta3)
    vector.create()
    assert len(vector.data) == 0
    with raises(AssertionError):
        vector.create()

    # test meta index
    index_vector = Vector()
    index_meta1 = Metadata((2, 3), types.address)
    index_meta0 = Metadata((0, 2), types.address) # empty meta
    index_meta2 = Metadata((3, 2), types.address)
    index_vector.add(index_meta1)
    index_vector.add(index_meta0)
    index_vector.add(index_meta2)
    index_vector.create()
    for i in xrange(12):
        index_vector.data[i] = i
    with raises(IndexError):
        index_meta1[6] = 20
    with raises(IndexError):
        index_meta1[-1] = 20
    with raises(IndexError):
        index_meta1[0, 3] = 20
    with raises(IndexError):
        index_meta1[2, 0] = 20
    assert [_ for _ in index_meta1] == [0, 1, 2, 3, 4, 5]
    assert [_ for _ in index_meta2] == [6, 7, 8, 9, 10, 11]
    assert [0, 1, 2, 3, 4, 5] == [
        index_meta1[0, 0], index_meta1[1, 0],
        index_meta1[0, 1], index_meta1[1, 1],
        index_meta1[0, 2], index_meta1[1, 2],
    ]
    index_meta2[2, 1] = 12
    assert [6, 7, 8, 9, 10, 12] == [
        index_meta2[0, 0], index_meta2[1, 0], index_meta2[2, 0],
        index_meta2[0, 1], index_meta2[1, 1], index_meta2[2, 1],
    ]
    with raises(IndexError):
        index_meta0[0, 0] = 20
    with raises(IndexError):
        index_meta0[0] = 20
    assert [_ for _ in index_meta0] == []

    # addresses
    with raises(IndexError):
        index_meta1.to_address(2, 0)
    assert index_meta1.to_address(0, 0) == 0
    assert index_meta1.to_address(1, 0) == 1
    assert index_meta1.to_address(0, 1) == 2
    assert index_meta2.to_address(0, 0) == 6

