# -*- coding: utf-8 -*-
"""
Random input device
"""
cl = None
try:
    import pyopencl as cl
except ImportError:
    pass
from openre.device.opencl import OpenCL
import numpy
from openre import neurons
from openre.templates import create_env
from openre.data_types import types, null
from openre.vector import Vector

class NumpyInput(OpenCL):
    """
    Just fill the transmitter index with random spikes
    """
    def __init__(self, config):
        super(NumpyInput, self).__init__(config)
        self.data_vector = Vector()
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

        # self.config

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
    device2 = ore.domains[1].device
    D1 = ore.domains[0]
    D2 = ore.domains[1]
    ore.tick()
    D2.neurons.from_device(device2)
    # receiver neurons in D2 is spiked the same as spikes data in
    # D1.transmitter_index
    assert list((D1.transmitter_index.is_spiked.data + 1) & neurons.IS_SPIKED) \
            == list(D2.neurons.flags.data[100:] & neurons.IS_SPIKED)
    ore.tick()
    D2.neurons.from_device(device2)
    # at least one spike should happen
    assert sum(list(D2.neurons.flags.data[0:100] & neurons.IS_SPIKED))
