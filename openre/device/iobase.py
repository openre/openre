# -*- coding: utf-8 -*-
"""
Base for numpy input and output devices
"""
from openre.device.abstract import Device
import numpy as np
from openre.vector import StandaloneVector
from copy import deepcopy
from threading import Thread


class InputRow(object):
    """
    Store input data in instances of this class
    """
    def __init__(self, config):
        self.config = config
        self.input_data = None
        self.input_data_cache = None
        self.input_expire = 0
        self.input_expire_per = self.config.get('expire', 0)
        self.width = self.config['width']
        self.height = self.config['height']
        self.length = self.width * self.height


class IOBase(Device):
    """
    Base class for numpy input and output devices
    """

    def __init__(self, config):
        super(IOBase, self).__init__(config)
        self._output_cache = None
        self.input = []  # input data from other domains
        self.output = None  # output data from this domain
        self._input = []
        width = self.config.get('width', 0)
        height = self.config.get('height', 0)
        if 'input' in self.config:
            if not isinstance(self.config['input'], (list, tuple)):
                self.config['input'] = [self.config['input']]
            for row in self.config['input']:
                row = deepcopy(row)
                row['width'] = row.get('width', width)
                row['height'] = row.get('height', height)
                self._input.append(InputRow(row))

    def tick_neurons(self, domain):
        self.tick_output_data(domain)
        self.tick_input_data(domain)

    def tick_output_data(self, domain):
        """
        Send data from our device to other domains
        """
        rows = self.data_to_send_ex(domain)
        if not rows:
            return
        # find all data consumers by source attribute and cache it
        if self._output_cache is None:
            self._output_cache = {}
            cache = self._output_cache
            for output_config in self.config['output']:
                source_id = output_config['name']
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
                for input_index, input_row in enumerate(
                    other_domain.config['device'].get('input', [])
                ):
                    source_id = input_row['name']
                    # not our source
                    if source_id not in cache:
                        continue
                    cache[source_id].append([other_domain, input_index])

        cache = self._output_cache
        for source_id, data in rows:
            for consumer_domain, layer_index in cache[source_id]:
                consumer_domain.register_input_layer_data(layer_index, data)

    def tick_input_data(self, domain):
        """
        Run once. If we have config for input - then we will be calling
        self._tick_input_data, otherwise this will become dummy method
        """
        if self._input:
            self.tick_input_data = self._tick_input_data
        else:
            self.tick_input_data = lambda domain: None
        return self.tick_input_data(domain)

    def _tick_input_data(self, domain):
        """
        Process data from other domains
        """
        ticks = domain.ticks
        ret = []
        for layer in self._input:
            if layer.input_data is None and layer.input_data_cache is None:
                continue
            data = layer.input_data
            layer.input_data = None
            input_data_vector = layer.input_data_cache
            if input_data_vector is None:
                input_data_vector = StandaloneVector()
                if isinstance(data, basestring):
                    input_data_vector.from_bytes(data)
                else:
                    input_data_vector.set_data(data)
                assert len(input_data_vector) == layer.length, \
                    "Domain '%s': len(input_data_vector) = %s, " \
                    "layer.length = %s" \
                    % (domain.name, len(input_data_vector), layer.length)
                layer.input_data_cache = input_data_vector
            length = len(input_data_vector)
            if not length:
                return
            ret.append([
                layer.config['name'],
                np.reshape(input_data_vector.data, (layer.height, layer.width))
            ])
            if layer.input_expire <= ticks:
                layer.input_data = None
                layer.input_data_cache = None
        if ret:
            self.receive_data(domain, ret)


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
        data = self.data_to_send(domain)
        if data is None:
            return
        if not len(data):
            return
        for output_config in self.config['output']:
            source_id = output_config['name']
            if 'shape' in output_config:
                from_x, from_y, width, height = output_config['shape']
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
        if needed and return.
        """
        # disable method
        self.tick_output_data = lambda domain: None

    def receive_data(self, domain, data):
        """
        Here we process incoming data.
        data: [source_id, numpy_array]
        """
        # disable method
        self.tick_input_data = lambda domain: None

    def register_input_data(self, input_index, data, domain_ticks):
        """
        Set self.input_data to received data.
        All previous data will be discarded.
        """
        input_row = self._input[input_index]
        input_row.input_data = data
        input_row.input_data_cache = None
        input_row.input_expire = domain_ticks + input_row.input_expire_per


class IOThreadBase(IOBase):
    def __init__(self, config):
        super(IOThreadBase, self).__init__(config)
        self._start = None
        self._thread = None
        self.start()

    def start(self):
        if self._start:
            return
        self._start = True
        self._thread = Thread(target=self._update, args=())
        self._thread.start()

    def stop(self):
        self._start = False
        self._thread.join()

    def init(self):
        """
        Init inside thread
        """

    def update(self):
        self.stop()
        self.tick_input_data = lambda domain: None
        self.tick_output_data = lambda domain: None

    def _update(self):
        self.init()
        update = self.update
        while self._start:
            update()

    def clean(self):
        super(IOThreadBase, self).clean()
        self.stop()

    def data_to_send(self, domain):
        return self.output

    def receive_data(self, domain, data):
        self.input = data


class IOBaseTesterLowLevel(IOBase):
    def data_to_send_ex(self, domain):
        ret = []
        length = 0
        assert self.config['width'] == 16
        assert self.config['height'] == 10
        for source_index, output_config in enumerate(self.config['output']):
            source_id = output_config['name']
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
                'relaxation': 0,
            },
        ],
        'domains': [
            {
                'name'        : 'D1',
                'device'    : {
                    'type': device_type,
                    'width': 16,
                    'height': 10,
                    'output': [
                        # [c1 c2]
                        # [c3 c4]
                        {'name': 'c1', 'shape': [0, 0, 8, 5]},
                        {'name': 'c2', 'shape': [8, 0, 8, 5]},
                        {'name': 'c3', 'shape': [0, 5, 8, 5]},
                        {'name': 'c4', 'shape': [8, 5, 8, 5]},
                    ],
                },
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


