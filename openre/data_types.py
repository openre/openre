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
        self.sinapse_level = np.uint16
        self.medium_address = np.uint16
        self.address = np.uint32
        self.tick = np.uint32
        self.vitality = np.uint32

    def max(self, type):
        return np.iinfo(type).max

types = DataTypes()

# Константы (могут быть разными в разных доменах):
null = types.max(types.address)

def test_data_types():
    assert null == np.iinfo(types.address).max
