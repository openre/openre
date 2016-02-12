# -*- coding: utf-8 -*-
"""
Base for numpy input and output devices
"""
from openre.device.abstract import Device

class IOBase(Device):
    """
    Base class for numpy input and output devices
    """
    def tick_neurons(self, domain):
        pass

    def tick_synapses(self, domain):
        pass

    def tick_transmitter_index(self, domain):
        pass

    def tick_receiver_index(self, domain):
        pass

    def create(self, data):
        if not len(data):
            return None
        return data

    def upload(self, device_data_pointer, data, is_blocking=True):
        pass

    def download(self, data, device_data_pointer, is_blocking=True):
        pass
