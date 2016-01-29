# -*- coding: utf-8 -*-
"""
Random input device
"""
from openre.device.abstract import Device
import numpy
from openre import neurons

class Random(Device):
    """
    Just fill the transmitter index with random spikes
    """
    def __init__(self, config):
        super(Random, self).__init__(config)
        method = 'random'
        args = []
        if self.config.get('method'):
            method = self.config['method']
        if not hasattr(numpy.random, method):
            raise ValueError('Wrong method %s for random device' % method)
        if 'args' in self.config:
            args = self.config['args']
        func = getattr(numpy.random, method)
        threshold = self.config.get('threshold', 0.5)
        def fill_transmitter_index(data):
            size = self.config.get('size', len(data))
            if not size is None:
                rnd_data = func(*args, size=size)
            else:
                rnd_data = func(*args)

            for pos, flag in enumerate(data):
                if rnd_data[pos] >= threshold:
                    data[pos] = 1
                else:
                    data[pos] = 0
        self.fill_transmitter_index = fill_transmitter_index

    def tick_neurons(self, domain):
        pass

    def tick_synapses(self, domain):
        pass

    def tick_transmitter_index(self, domain):
        length = len(domain.transmitter_index.local_address)
        if not length:
            return
        self.fill_transmitter_index(
            domain.transmitter_index.is_spiked.data
        )

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

def test_random_device():
    from openre import OpenRE
    # remote domains
    config = {
        'layers': [
            {
                'name': 'R1',
                'width': 20,
                'height': 20,
                'is_inhibitory': False,
                'connect': [
                    {
                        'name': 'V2',
                        'radius': 1,
                        'shift': [0, 0],
                    },
                ],
            },
            {
                'name': 'V2',
                'width': 20,
                'height': 20,
            },
        ],
        'domains': [
            {
                'name'        : 'D1',
                'device'    : {
                    'type': 'Random',
                },
                'layers'    : [
                    {'name': 'R1'},
                ],
            },
            {
                'name'        : 'D2',
                'device'    : {
                    'type': 'OpenCL',
                },
                'layers'    : [
                    {'name': 'V2'},
                ],
            },
        ],
    }
    ore = OpenRE(config)
    ore.deploy()
    device2 = ore.domains[1].device
    D1 = ore.domains[0]
    D2 = ore.domains[1]
    ore.tick()
    D2.neurons.from_device(device2)
    # receiver neurons in D2 is spiked the same as spikes data in
    # D1.transmitter_index
    assert list((D1.transmitter_index.is_spiked.data + 1) & neurons.IS_SPIKED) \
            == list(D2.neurons.flags.data[400:] & neurons.IS_SPIKED)
    ore.tick()
    D2.neurons.from_device(device2)
    # at least one spike should happen
    assert sum(list(D2.neurons.flags.data[0:400] & neurons.IS_SPIKED))
