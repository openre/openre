# -*- coding: utf-8 -*-
"""
Массив данных для моделирования нейронов (представляет из себя объект, который
содержит по одному вектору на каждый из параметров нейрона)
"""
from openre.metadata import Metadata
from openre.vector import Vector
from openre.data_types import types

class NeuronsVector(object):
    """
    Нейрон (neuron) - упрощенная модель биологического нейрона. На данный
    момент, это простой сумматор.
    level: types.neuron_level - уровень возбуждения нейрона
    flags: types.neuron_flags - флаги состояний нейрона
        IS_INHIBITORY   = 1<<0 - если бит установлен, то нейрон тормозящий
        IS_SPIKED       = 1<<1 - если бит установлен, то произошел спайк
        IS_DEAD         = 1<<2 - если бит установлен, то нейрон мертв и никак
                                 не обрабатывает приходящие сигналы
        IS_TRANSMITTER  = 1<<3 - если бит установлен, то синапсы нейрона
                                 находятся в другом домене, передающая часть
                                 выступает как post-нейрон в синапсе,
                                 информация о спайке пересылается с помощью
                                 сообщений, такой нейрон может быть
                                 pre-нейроном в синапсе.
        IS_RECEIVER     = 1<<4 - если бит установлен, то тело нейрона находится
                                 в другом домене, принимающая часть выступает
                                 как pre-нейрон в синапсе. Не может быть
                                 post-нейроном в синапсе, при попытке создать
                                 такую связь должно гененрироваться исключение.
    spike_tick: types.tick - номер тика, при котором произошел спайк
    """

    def __init__(self):
        self.level = Vector(types.neuron_level)
        self.flags = Vector(types.neuron_flags)
        self.spike_tick = Vector(types.tick)
        self.length = 0

    def add(self, metadata):
        """
        Добавляем метаданные нейронов в слое в вектор
        """
        self.level.add(metadata.level)
        self.flags.add(metadata.flags)
        self.spike_tick.add(metadata.spike_tick)
        metadata.address = metadata.level.address
        self.length = self.level.length

    def __len__(self):
        return self.length

    def create(self):
        """
        Выделяем в памяти буфер под данные
        """
        self.level.create()
        self.flags.create()
        self.spike_tick.create()


class NeuronsMetadata(object):
    """
    Метаданные для одного слоя нейронов
    """

    def __init__(self, layer):
        self.level = Metadata((layer.width, layer.height), types.neuron_level)
        self.flags = Metadata((layer.width, layer.height), types.neuron_flags)
        self.spike_tick = Metadata((layer.width, layer.height), types.tick)
        self.address = None

