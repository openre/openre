# -*- coding: utf-8 -*-
"""
Массив данных для моделирования нейронов (представляет из себя объект, который
содержит по одному вектору на каждый из параметров нейрона)
"""
from openre.metadata import MultiFieldMetadata
from openre.vector import MultiFieldVector
from openre.data_types import types

IS_INHIBITORY = 1<<0
IS_SPIKED = 1<<1
IS_DEAD = 1<<2
IS_TRANSMITTER = 1<<3
IS_RECEIVER = 1<<4
IS_INFINITE_ERROR = 1<<5

class NeuronsVector(MultiFieldVector):
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
        IS_INFINITE_ERROR = 1<<5 - если бит установлен, значит при последнем
                                 обсчете device.tick_sinapses для этого нейрона
                                 был бесконечный цикл.
    spike_tick: types.tick - номер тика, при котором произошел спайк
    """

    fields = [
        ('level', types.neuron_level),
        ('flags', types.neuron_flags),
        ('spike_tick', types.tick),
        ('layer', types.medium_address),
    ]

class NeuronsMetadata(MultiFieldMetadata):
    """
    Метаданные для одного слоя нейронов
    """
    fields = list(NeuronsVector.fields)

