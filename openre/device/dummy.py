# -*- coding: utf-8 -*-
"""
Dummy device
"""

from openre.device.abstract import Device

class Dummy(Device):
    def tick_neurons(self, domain):
        pass

    def tick_sinapses(self, domain):
        pass

    def upload(self, data):
        # Do not upload empty buffers
        if not len(data):
            return None
        return data

    def download(self, data, device_data_pointer):
        if device_data_pointer is None:
            return
        data[:] = device_data_pointer

