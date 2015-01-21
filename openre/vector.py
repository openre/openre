# -*- coding: utf-8 -*-
"""
Вектор
"""
import numpy as np

class Vector(object):
    """
    Хранит в себе одномерный массив, который можно копировать на устройство
    и с устройства.
    """

    def __init__(self):
        self.length = 0
        self.metadata = []
        self.data = None
        self.type = None

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
        address = self.length
        self.metadata.append(metadata)
        self.length += metadata.shape[0]*metadata.shape[1]
        metadata.set_address(self, address)

    def create(self):
        """
        Создает в памяти вектор заданного типа и помещает его в self.data
        """
        assert self.length
        assert self.data is None
        self.data = np.zeros((self.length, 1)).astype(self.type)

    def to_device(self):
        """
        Копирует данные из self.data в устройство
        """

    def from_device(self):
        """
        Копирует данные из устройства в self.data
        """


def test_vector():
    from openre.metadata import Metadata
    from openre.data_types import types
    from pytest import raises

    meta0 = Metadata((10, 20), types.index_flags)
    meta1 = Metadata((25, 15), types.index_flags)
    assert meta0.address is None

    vector = Vector()
    assert vector.type is None
    with raises(AssertionError):
        vector.create()
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

