# -*- coding: utf-8 -*-
"""
Массив данных для моделирования синапсов
"""
from openre.metadata import MultiFieldExtendableMetadata
from openre.vector import Vector, RandomIntVector, MultiFieldVector
from openre.data_types import types

IS_STRENGTHENED = 1<<0

class SynapsesVector(MultiFieldVector):
    """
    Синапс (synapse) - Содержит информацию о связи между двумя нейронами -
    pre- и post-нейроном с определенной силой (level). Если у pre-нейрона
    произошел спайк, то post-нейрон увеличивает или уменьшает (зависит от
    типа pre-нейрона, тормозящий он или возбуждающий) свой уровень
    на synapse.level
    level: types.synapse_level - сила с которой синапс передает возбуждение
           к post-нейрону
    pre: types.address - адрес pre-нейрона внутри одного домена
    post: types.address - адрес post-нейрона внутри одного домена
    """
    fields = [
        ('level', types.synapse_level),
        ('pre', types.address),
        ('post', types.address),
        ('learn', types.synapse_level),
        ('flags', types.synapse_flags),
    ]
    def __init__(self, low, high=None):
        assert self.__class__.fields
        for field, field_type in self.__class__.fields:
            if field == 'level':
                setattr(self, field, RandomIntVector(field_type,
                                                     low, high=high))
            else:
                setattr(self, field, Vector(field_type))
        self.length = 0

    def create(self, low, high=None):
        """
        Выделяем в памяти буфер под данные
        """
        for field, _ in self.__class__.fields:
            if field == 'level':
                getattr(self, field).create(low, high)
            else:
                getattr(self, field).create()

class SynapsesMetadata(MultiFieldExtendableMetadata):
    """
    Метаданные для нейронов
    """
    fields = list(SynapsesVector.fields)
