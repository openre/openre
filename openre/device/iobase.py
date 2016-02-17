# -*- coding: utf-8 -*-
"""
Base for numpy input and output devices
"""
from openre.device.abstract import Device
import numpy as np

class IOBase(Device):
    """
    Base class for numpy input and output devices
    """

    def __init__(self, config):
        super(IOBase, self).__init__(config)
        self._source_cache = None

    def tick_neurons(self, domain):
        rows = self.data_to_send_ex(domain)
        if not rows:
            return
        # find all source consumers and cache it
        if self._source_cache is None:
            self._source_cache = {}
            cache = self._source_cache
            for source_config in domain.config['sources']:
                source_id = source_config['name']
                cache[source_id] = []
            net = domain.net
            # consumers
            for other_domain in net.domains:
                # can't send to itself
                if other_domain == domain:
                    continue
                for layer_index, layer in enumerate(other_domain.layers):
                    if not layer.config.get('input'):
                        continue
                    source_id = layer.config['input']
                    # not our source
                    if source_id not in cache:
                        continue
                    cache[source_id].append([other_domain, layer_index])

        cache = self._source_cache
        for source_id, data in rows:
            for consumer_domain, layer_index in cache[source_id]:
                consumer_domain.register_input_layer_data(layer_index, data)



    def tick_synapses(self, domain):
        pass

    def tick_transmitter_index(self, domain):
        pass

    def tick_receiver_index(self, domain):
        pass

    def create(self, data):
        if data is None:
            return None
        if not len(data):
            return None
        return data

    def upload(self, device_data_pointer, data, is_blocking=True):
        pass

    def download(self, data, device_data_pointer, is_blocking=True):
        pass

    def data_to_send_ex(self, domain):
        """
        Redefine this for a low level control of data you want to generate
        to send to other domains
        Should return:
            [
                [source_id, binary_data],
                ...
            ]
        """
        ret = []
        domain_config = domain.config
        data = self.data_to_send(domain)
        if data is None:
            return
        if not len(data):
            return
        for source_index, source_config in enumerate(domain_config['sources']):
            source_id = source_config['name']
            if 'shape' in source_config:
                from_x, from_y, width, height = source_config['shape']
                part = data[from_y:from_y+height, from_x:from_x+width]
            else:
                part = data
            ret.append([source_id, part])
        return ret

    def data_to_send(self, domain):
        """
        Most time you need to redefine only this method for source devices.
        You need to return numpy array with given
        self.config['width'] x self.config['height']
        For example: in devices like camera - here you take frame from
        previously initialized device, resize it to given width and height
        and return.
        """
        raise NotImplementedError


class IOBaseTesterLowLevel(IOBase):
    def data_to_send_ex(self, domain):
        ret = []
        domain_config = domain.config
        length = 0
        assert self.config['width'] == 16
        assert self.config['height'] == 10
        for source_index, source_config in enumerate(domain_config['sources']):
            source_id = source_config['name']
            area_length = 8*5
            data = np.zeros(area_length).astype(np.uint8)
            data.fill(source_index)
            ret.append([source_id, data])
            length += area_length
        assert length == 16*10
        return ret

class IOBaseTesterSimple(IOBase):
    def data_to_send(self, domain):
        assert self.config['width'] == 16
        assert self.config['height'] == 10
        arr = np.zeros((10, 16), dtype=np.uint8)
        arr[0:5, 0:8] = 0
        arr[0:5, 8:16] = 1
        arr[5:10, 0:8] = 2
        arr[5:10, 8:16] = 3
        return arr

class IOBaseTesterSimpleSlow(IOBaseTesterSimple):
    def data_to_send(self, domain):
        import time
        time.sleep(0.01)
        return super(IOBaseTesterSimpleSlow, self).data_to_send(domain)

def test_iobase_device_send_data():
    _test_iobase_device('IOBaseTesterLowLevel')

def test_iobase_device_simple():
    _test_iobase_device('IOBaseTesterSimple')

def _test_iobase_device(device_type):
    from openre import OpenRE
    config = {
        'layers': [
            {
                'name': 'V1',
                'width': 16,
                'height': 10,
            },
        ],
        'domains': [
            {
                'name'        : 'D1',
                'device'    : {
                    'type': device_type,
                    'width': 16,
                    'height': 10,
                },
                'sources': [
                    # [c1 c2]
                    # [c3 c4]
                    {'name': 'c1', 'shape': [0, 0, 8, 5]},
                    {'name': 'c2', 'shape': [8, 0, 8, 5]},
                    {'name': 'c3', 'shape': [0, 5, 8, 5]},
                    {'name': 'c4', 'shape': [8, 5, 8, 5]},
                ],
            },
            {
                'name'        : 'D2',
                'device'    : {
                    'type': 'OpenCL',
                },
                'layers'    : [
                    {'name': 'V1', 'input': 'c1', 'shape': [0, 0, 8, 5]},
                    {'name': 'V1', 'input': 'c2', 'shape': [8, 0, 8, 5]},
                    {'name': 'V1', 'input': 'c3', 'shape': [0, 5, 8, 5]},
                    {'name': 'V1', 'input': 'c4', 'shape': [8, 5, 8, 5]},
                ],
            },
        ],
    }
    ore = OpenRE(config)
    ore.deploy()
    device1 = ore.domains[0].device
    device2 = ore.domains[1].device
    D1 = ore.domains[0]
    D2 = ore.domains[1]
    D2.neurons.level.data[:] = 0
    D2.neurons.level.to_device(device2)
    ore.tick()

    D1.neurons.from_device(device1)
    D2.neurons.from_device(device2)
    for layer_index, layer in enumerate(D2.layers):
        for x in xrange(8):
            for y in xrange(5):
                assert layer.neurons_metadata.level[x, y] == layer_index


