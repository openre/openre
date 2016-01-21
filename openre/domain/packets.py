# -*- coding: utf-8 -*-

from openre.metadata import MultiFieldExtendableMetadata
from openre.vector import MultiFieldVector
from openre.data_types import types

class TransmitterVector(MultiFieldVector):
    """
    Вектор для IS_TRANSMITTER нейронов.
    Используется в remote_domain.send_synapse
    """
    fields = [
        ('pre_domain_index', types.medium_address),
        ('pre_layer_index', types.medium_address),
        ('pre_neuron_address', types.address),
        ('post_layer_index', types.medium_address),
        ('post_x', types.address),
        ('post_y', types.address),
    ]

class TransmitterMetadata(MultiFieldExtendableMetadata):
    """
    Метаданные для IS_TRANSMITTER нейронов
    """
    fields = list(TransmitterVector.fields)

class ReceiverVector(MultiFieldVector):
    """
    Вектор для IS_RECEIVER нейронов.
    Используется в remote_domain.send_receiver_index
    """
    fields = [
        ('post_domain_index', types.medium_address),
        ('pre_neuron_address', types.address),
        ('remote_pre_neuron_address', types.address),
        ('remote_pre_neuron_receiver_index', types.address),
    ]

class ReceiverMetadata(MultiFieldExtendableMetadata):
    """
    Метаданные для IS_RECEIVER нейронов
    """
    fields = list(ReceiverVector.fields)

class SpikesVector(MultiFieldVector):
    """
    Вектор для IS_SPIKED нейронов.
    Используется в remote_domain.send_spikes и local_domain.receive_spikes
    """
    fields = [
        ('receiver_neuron_index', types.address),
    ]

class SpikesMetadata(MultiFieldExtendableMetadata):
    """
    Метаданные для IS_SPIKED нейронов
    """
    fields = list(SpikesVector.fields)

