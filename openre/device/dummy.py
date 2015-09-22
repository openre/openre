# -*- coding: utf-8 -*-
"""
Dummy device
"""

from openre.device.abstract import Device

class Dummy(Device):
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
        # Do not upload empty buffers
        if not len(data):
            return
        device_data_pointer[:] = data

    def download(self, data, device_data_pointer, is_blocking=True):
        if device_data_pointer is None:
            return
        data[:] = device_data_pointer

