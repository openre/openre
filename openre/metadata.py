# -*- coding: utf-8 -*-
"""
Метаданные.
"""

class Metadata(object):
    """
    Метаданные для части данных, хранящихся в векторе (vector).
    Например это может быть двухмерный массив нейронов. Класс позволяет
    сохранить изначальные размеры массива после преобразования его в вектор и
    упрощает преобразование координат элемента в двухмерном массиве в адрес
    элемента в векторе. В основном это понадобится при связывании двух слоев
    нейронов посредством синапсов.
    self.shape - изначальная форма массива. Например: shape = (x, y),
                 где x - это ширина, y - высота.
    self.type - тип данных. Один из openre.data_types.types.
    self.address - адрес элемента c координатами (0,0) в векторе.
    self.vector - вектор, в котором хранятся метаданные. Добавление метаданных в
                  вектор происходит через vector.add(metadata)
    """

    def __init__(self, shape, type):
        self.shape = shape
        self.length = self.shape[0] * self.shape[1]
        self.type = type
        self.address = None
        self.vector = None

    def set_address(self, vector, address):
        """
        Вызывается из вектора и устанавливает адрес (address) первого элемента в
        векторе vector. Вектор так же сохраняется.
        """
        self.address = address
        self.vector = vector

    def __len__(self):
        return self.length

    def __getitem__(self, key):
        if isinstance(key, (tuple, list)):
            if key[0] < 0 or key[0] >= self.shape[0]:
                raise IndexError
            if key[1] < 0 or key[1] >= self.shape[1]:
                raise IndexError
        else:
            if key < 0 or key >= self.length:
                raise IndexError
            key = (key, 0)
        return self.vector[self.address + key[0] + key[1]*self.shape[0]]

    def __setitem__(self, key, value):
        if isinstance(key, (tuple, list)):
            if key[0] < 0 or key[0] >= self.shape[0]:
                raise IndexError
            if key[1] < 0 or key[1] >= self.shape[1]:
                raise IndexError
        else:
            if key < 0 or key >= self.length:
                raise IndexError
            key = (key, 0)
        self.vector[self.address + key[0] + key[1]*self.shape[0]] = value

