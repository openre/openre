# -*- coding: utf-8 -*-
"""
Массив данных для моделирования нейронов (представляет из себя объект, который
содержит по одному вектору на каждый из параметров нейрона)
"""
from openre.metadata import MultiFieldMetadata, MultiFieldExtendableMetadata
from openre.vector import MultiFieldVector
from openre.data_types import types
import random

IS_INHIBITORY = 1<<0
IS_SPIKED = 1<<1
IS_DEAD = 1<<2
IS_TRANSMITTER = 1<<3
IS_RECEIVER = 1<<4
IS_INFINITE_ERROR = 1<<5

def create_neuron(address, neurons_metadata, layer, layer_index):
    neurons_metadata.level[address] \
            = int(random.random() * (layer.threshold + 1))
    neurons_metadata.flags[address] = 0
    if layer.is_inhibitory:
        neurons_metadata.flags[address] |= IS_INHIBITORY
    neurons_metadata.layer[address] = layer_index
    neurons_metadata.vitality[address] = layer.max_vitality


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
        IS_TRANSMITTER  = 1<<3 - если бит установлен, то как минимум один синапс
                                 нейрона находятся в другом домене,
                                 передающая часть выступает как post-нейрон в
                                 синапсе, информация о спайке пересылается с
                                 помощью сообщений, такой нейрон может быть
                                 pre-нейроном в синапсе.
        IS_RECEIVER     = 1<<4 - если бит установлен, то тело нейрона находится
                                 в другом домене, принимающая часть выступает
                                 как pre-нейрон в синапсе. Не может быть
                                 post-нейроном в синапсе, при попытке создать
                                 такую связь должно гененрироваться исключение.
    spike_tick: types.tick - номер тика, при котором произошел спайк
    layer: types.medium_address - адрес слоя, к которому принадлежит нейрон
    vitality: types.vitality - количество питательных веществ у нейрона.
                               Максимум - max_vitality. При достижении слишком
                               маленького значениея нейрон умирает
                               (устанавливается флаг IS_DEAD)
    """

    fields = [
        ('level', types.neuron_level),
        ('flags', types.neuron_flags),
        ('spike_tick', types.tick),
        ('layer', types.medium_address),
        ('vitality', types.vitality),
    ]

class NeuronsMetadata(MultiFieldMetadata):
    """
    Метаданные для одного слоя нейронов
    """
    fields = list(NeuronsVector.fields)

class NeuronsExtendableMetadata(MultiFieldExtendableMetadata):
    """
    Метаданные для нейронов из другого домена
    """
    fields = list(NeuronsVector.fields)

