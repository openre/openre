# -*- coding: utf-8 -*-
"""
Вектор
"""
import numpy as np
from openre.errors import OreError
from openre.metadata import ExtendableMetadata

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
        for m in self.metadata:
            if isinstance(m, ExtendableMetadata):
                raise OreError('You can add only one extendable metadata and ' \
                               'it should be the last one')
        if metadata.vector:
            raise OreError('Metadata already assigned to vector')
        if self.data is None:
            self.create()
        address = self.length
        self.metadata.append(metadata)
        self.resize(portion=metadata.length)
        metadata.set_address(self, address)

    def __len__(self):
        return self.length

    def create(self):
        """
        Создает в памяти вектор заданного типа и помещает его в self.data
        """
        if not self.data is None:
            return
        assert self.data is None
        self.data = np.zeros((1)).astype(self.type)

    def shrink(self):
        length = 0
        for metadata in self.metadata:
            length += metadata.length
        if self.length == length:
            return
        self.length = length
        self.data.resize((self.length), refcheck=False)

    def resize(self, portion):
        self.length += portion
        self.data.resize((self.length), refcheck=False)

    def create_device_data_pointer(self, device):
        """
        Создает self.device_data_pointer для устройства device
        """
        self.shrink()
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
    def __init__(self, type=None, low=None, high=None):
        super(RandomIntVector, self).__init__(type=type)
        assert not low is None
        self.low = low
        self.high = high

    def resize(self, portion):
        super(RandomIntVector, self).resize(portion=portion)
        self.data[self.length-portion:self.length] = np.random.random_integers(
            self.low, high=self.high, size=(portion))

    def create(self):
        """
        Создает в памяти вектор заданного типа и помещает его в self.data
        """
        if not self.data is None:
            return
        assert self.data is None
        self.data = np.random.random_integers(
            self.low, high=self.high, size=(self.length)).astype(self.type)

class MultiFieldVector(object):
    """
    Вектор с несколькими полями одинаковой длины. Для каждого поля можно
    задавать свой тип.
    """
    fields = []
    def __init__(self):
        assert self.__class__.fields
        for field, field_type in self.__class__.fields:
            setattr(self, field, Vector(field_type))
        self.length = 0

    def add(self, metadata):
        """
        Добавляем метаданные
        """
        for field, _ in self.__class__.fields:
            getattr(self, field).add(getattr(metadata, field))
        field, _ = self.__class__.fields[0]
        metadata.address = getattr(metadata, field).address
        self.length = getattr(self, field).length

    def __len__(self):
        return self.length

    def shrink(self):
        """
        Уменьшаем буфер и делаем его равным длине всех метаданных
        """
        for field, _ in self.__class__.fields:
            getattr(self, field).shrink()

    def create(self):
        """
        Выделяем в памяти буфер под данные
        """
        for field, _ in self.__class__.fields:
            getattr(self, field).create()

    def create_device_data_pointer(self, device):
        """
        Создание указателей на данные на устройстве
        """
        for field, _ in self.__class__.fields:
            getattr(self, field).create_device_data_pointer(device)

    def to_device(self, device):
        """
        Загрузка на устройство
        """
        for field, _ in self.__class__.fields:
            getattr(self, field).to_device(device)

    def from_device(self, device):
        """
        Выгрузка с устройства
        """
        for field, _ in self.__class__.fields:
            getattr(self, field).from_device(device)


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
        assert len(vector.data) == vector.length
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
    vector.create() # second call do nothing
    assert len(vector.data) == 10*20 + 25*15
    vector2 = Vector(types.index_flags)
    assert vector2.type == types.index_flags


    vector = Vector()
    meta3 = Metadata((0, 0), types.index_flags)
    with raises(OreError):
        vector.add(meta0)
    vector.add(meta3)
    vector.create()
    assert len(vector.data) == 0
    vector.create() # second call do nothing
    assert len(vector.data) == 0

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

    # RandomIntVector
    meta0 = Metadata((10, 20), types.index_flags)
    meta1 = Metadata((25, 15), types.index_flags)
    assert meta0.address is None

    vector = RandomIntVector(None, 1, 5)
    assert vector.type is None
    vector.add(meta0)
    assert vector.type == meta0.type
    assert meta0.address == 0
    assert len(vector.data) == meta0.length
    assert type(vector.data[0]) == types.index_flags
    vector.add(meta1)
    assert 0 not in vector.data

    # ExtendableMetadata
    vector = Vector()
    meta0 = ExtendableMetadata((2, 2), types.index_flags)
    vector.add(meta0)
    meta1 = ExtendableMetadata((10, 20), types.index_flags)
    with raises(OreError):
        vector.add(meta1)
    meta0[0,0] = 1
    assert vector.length == meta0.length
    assert vector.length == 2*2
    assert [_ for _ in vector.data] == [1, 0, 0, 0]
    meta0[2,0] = 2
    assert [_ for _ in vector.data] == [1, 0, 2, 0, 0, 0, 0, 0]
    assert meta0.length == 3*2
    assert vector.length == 2*2*2
    meta0[0,3] = 3
    assert [_ for _ in vector.data] == [1, 0, 2,
                                        0, 0, 0,
                                        0, 0, 0,
                                        3, 0, 0,
                                        0, 0, 0, 0]
    assert vector.length == 2*2*2*2
    assert meta0.length == 3*4

    vector.shrink()
    assert [_ for _ in vector.data] == [1, 0, 2,
                                        0, 0, 0,
                                        0, 0, 0,
                                        3, 0, 0,
                                       ]
    assert vector.length == 3*4
    assert meta0.length == 3*4


