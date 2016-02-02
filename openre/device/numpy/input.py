# -*- coding: utf-8 -*-
"""
Random input device
"""
cl = None
try:
    import pyopencl as cl
except ImportError:
    pass
from openre.templates import create_env
from openre.data_types import types, null


from openre.device.opencl import OpenCL
import numpy
from openre import neurons
from openre.vector import StandaloneVector

class NumpyInput(OpenCL):
    """
    Just fill the transmitter index with random spikes
    """
    def __init__(self, config):
        super(NumpyInput, self).__init__(config)
        self.data_vector = StandaloneVector()
        # self.config
        env = create_env()
        code = env.get_template("device/numpy.c").render(
            types=types,
            null=null
        )

        # compile the kernel for numpy device
        self.sub_program = cl.Program(self.ctx, code).build(
            options="-cl-denorms-are-zero " \
                    "-cl-no-signed-zeros " \
                    "-cl-finite-math-only"
        )

    def tick_neurons(self, domain):
        """
        Add value from self.data to neurons.level
        """
        if self.data_vector is None:
            return
        length = len(self.data_vector)
        if not length:
            return
        self.data_vector.to_device(self)
        # only one layer with the same dims as input data
        assert len(self.data_vector.data) == len(domain.neurons.level.data)
        self.sub_program.tick_numpy_input_data_uint8(
            self.queue, (length,), None,
            # data
            self.data_vector.device_data_pointer,
            # neurons
            domain.neurons.level.device_data_pointer
        ).wait()
        super(NumpyInput, self).tick_neurons(domain)

    def tick_transmitter_index(self, domain):
        length = len(domain.transmitter_index.local_address)
        if not length:
            return
        # fill this domain.transmitter_index.is_spiked.data

    def tick_receiver_index(self, domain):
        """
        This device do not receive spikes
        """
        pass

def test_numpy_input_device():
    from openre import OpenRE
    # remote domains
    config = {
        'layers': [
            {
                'name': 'Input',
                'width': 10,
                'height': 10,
                'is_inhibitory': False,
                'threshold': 128,
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
                'width': 10,
                'height': 10,
            },
        ],
        'domains': [
            {
                'name'        : 'D1',
                'device'    : {
                    'type': 'NumpyInput',
                },
                'layers'    : [
                    {'name': 'Input'},
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
    device1 = ore.domains[0].device
    device2 = ore.domains[1].device
    D1 = ore.domains[0]
    D2 = ore.domains[1]
    arr = numpy.arange(0, 200, 2, dtype=numpy.uint8)
    arr = StandaloneVector(numpy.reshape(arr, (10, 10)))
    assert arr.type == numpy.uint8
    packet = arr.bytes()
    # somewhere here we will send packet to the input device
    # and in input device will receive it:
    input_vector = D1.device.data_vector
    input_vector.from_bytes(packet)
    assert arr.type == input_vector.type
    assert list(input_vector.data) == list(arr.data)
    assert input_vector.length == 100
    assert len(input_vector) == input_vector.length
    assert len(D1.neurons.level) == len(input_vector)
    D1.neurons.level.data[:] = 0
    D1.neurons.level.to_device(device1)
    D2.neurons.level.data[:] = 0
    D2.neurons.level.to_device(device2)
    ore.tick()
    D1.neurons.from_device(device1)
    D2.neurons.from_device(device2)
    level_check = numpy.arange(0, 200, 2, dtype=numpy.uint8)
    level_check[level_check >= 128] = 0
    assert list(D1.neurons.level.data) == list(level_check)
    flags_check = numpy.arange(0, 200, 2, dtype=numpy.uint8)
    flags_check[flags_check < 128] = neurons.IS_TRANSMITTER
    flags_check[flags_check >= 128] = neurons.IS_TRANSMITTER | neurons.IS_SPIKED
    assert list(flags_check) == list(D1.neurons.flags.data)
    # check D2 neuron level
    # check D2 neuron level should be eq to synapses levels
    assert 0

