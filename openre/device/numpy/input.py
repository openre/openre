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


