# -*- coding: utf-8 -*-
"""
Массив данных для моделирования синапсов
"""
from openre.metadata import Metadata
from openre.vector import Vector
from openre.data_types import types


class SinapsesVector(object):
    """
    Синапс (sinapse) - Содержит информацию о связи между двумя нейронами -
    pre- и post-нейроном с определенной силой (level). Если у pre-нейрона
    произошел спайк, то post-нейрон увеличивает или уменьшает (зависит от
    типа pre-нейрона, тормозящий он или возбуждающий) свой уровень
    на sinapse.level
    level: types.sinapse_level - сила с которой синапс передает возбуждение
           к post-нейрону
    pre: types.address - адрес pre-нейрона внутри одного домена
    post: types.address - адрес post-нейрона внутри одного домена
    """

    def __init__(self):
        self.level = Vector(types.sinapse_level)
        self.pre = Vector(types.address)
        self.post = Vector(types.address)
        self.length = 0

    def add(self, metadata):
        """
        Добавляем метаданные синапсов в вектор
        """
        self.level.add(metadata.level)
        self.pre.add(metadata.pre)
        self.post.add(metadata.post)
        metadata.address = metadata.level.address
        self.length = self.level.length

    def __len__(self):
        return self.length

    def create(self):
        """
        Выделяем в памяти буфер под данные
        """
        self.level.create()
        self.pre.create()
        self.post.create()


class SinapsesMetadata(object):
    """
    Метаданные для нейронов
    """

    def __init__(self, length):
        self.level = Metadata((length, 1), types.sinapse_level)
        self.pre = Metadata((length, 1), types.address)
        self.post = Metadata((length, 1), types.address)
        self.address = None

