# -*- coding: utf-8 -*-
"""
Внутренние типы данных (могут быть разными в разных доменах).
Могут меняться, например, для экономии памяти.
"""
import numpy as np

class DataTypes(object):
    def __init__(self):
        self.stat = np.int64
        self.threshold = np.int32
        self.neuron_level = np.int32
        self.neuron_flags = np.uint8
        self.index_flags = np.uint8
        self.synapse_level = np.uint16
        self.synapse_flags = np.uint8
        self.medium_address = np.uint16
        self.address = np.uint32
        self.tick = np.uint32
        self.vitality = np.uint32
        self.allowed_input_data_type_names = [
            'int8', 'int16', 'int32', 'int64',
            'uint8', 'uint16', 'uint32', 'uint64']

        self.allowed_input_data_types = [
            getattr(np, name) for name in self.allowed_input_data_type_names]

    def is_allowed_input_data_type(self, np_type):
        if isinstance(np_type, basestring):
            np_type = getattr(np, np_type)
        return np_type in self.allowed_input_data_types

    def max(self, type):
        return np.iinfo(type).max

types = DataTypes()

# Константы (могут быть разными в разных доменах):
null = types.max(types.address)

def test_data_types():
    assert null == np.iinfo(types.address).max
