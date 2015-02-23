# -*- coding: utf-8 -*-
"""
Поддержка OpenCL устройств
"""
cl = None
try:
    import pyopencl as cl
except ImportError:
    pass
from openre.device.abstract import Device
from openre.templates import env
from openre.data_types import types

class OpenCL(Device):
    """
    Устройства, поддерживающие OpenCL
    """
    def __init__(self, config):
        super(OpenCL, self).__init__(config)
        if cl is None:
            raise ImportError('Install PyOpenCL to support OpenCL devices')
        platform_id = self.config.get('platform', 0)
        device_type = self.config.get('device_type')
        if device_type:
            self.device = cl.get_platforms()[platform_id].get_devices(
                getattr(cl.device_type, 'CPU'))[self.config.get('device', 0)]
        else:
            self.device = cl.get_platforms()[platform_id] \
                    .get_devices()[self.config.get('device', 0)]
        # create an OpenCL context
        self.ctx = cl.Context([self.device], dev_type=None)
        self.queue = cl.CommandQueue(self.ctx)
        code = env.get_template("device/opencl.c").render(
            types=types
        )

        # compile the kernel
        self.program = cl.Program(self.ctx, code).build(
            options="-cl-denorms-are-zero " \
                    "-cl-no-signed-zeros " \
                    "-cl-finite-math-only"
        )


    def tick_neurons(self, domain):
        self.program.tick_neurons(
            self.queue, (domain.neurons.length,), None,
            # domain
            types.tick(domain.ticks),
            # layers
            domain.layers_vector.threshold.device_data_pointer,
            domain.layers_vector.relaxation.device_data_pointer,
            domain.layers_vector.total_spikes.device_data_pointer,
            # neurons
            domain.neurons.level.device_data_pointer,
            domain.neurons.flags.device_data_pointer,
            domain.neurons.spike_tick.device_data_pointer,
            domain.neurons.layer.device_data_pointer
        ).wait()
        # download total_spikes from device and refresh layer.total_spikes
        domain.total_spikes = 0
        domain.layers_vector.total_spikes.from_device(self)
        for layer_id, layer in enumerate(domain.layers):
            layer.total_spikes = domain.layers_vector.total_spikes[layer_id]
            domain.total_spikes += layer.total_spikes
            # reset total_spikes in all layers and domain
            domain.layers_vector.total_spikes[layer_id] = 0
        # and upload it to device
        domain.layers_vector.total_spikes.to_device(self)

    def tick_sinapses(self, domain):
        self.program.tick_sinapses(self.queue, (domain.neurons.length,), None).wait()

    def create(self, data):
        if not len(data):
            return None
        return cl.Buffer(
            self.ctx,
            cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
            hostbuf=data
        )

    def upload(self, device_data_pointer, data, is_blocking=True):
        # Do not upload empty buffers
        if not len(data) or device_data_pointer is None:
            return
        cl.enqueue_copy(
            self.queue, device_data_pointer, data, is_blocking=is_blocking)

    def download(self, data, device_data_pointer, is_blocking=True):
        if device_data_pointer is None:
            return
        cl.enqueue_copy(
            self.queue, data, device_data_pointer, is_blocking=is_blocking)

def test_device():
    if cl is None:
        # skip test
        return
    from openre import OpenRE
    from pytest import raises
    import numpy as np
    from openre import neurons
    sinapse_max_level = 30000
    config = {
        'sinapse': {
            'max_level': sinapse_max_level
        },
        'layers': [
            {
                'id': 'V1',
                'threshold': sinapse_max_level,
                'relaxation': 1000,
                'width': 20,
                'height': 20,
                'connect': [
                    {
                        'id': 'V1',
                        'radius': 1,
                        'shift': [0, 0],
                    },
                ],
            },
        ],
        'domains': [
            {
                'id'        : 'D1',
                'device'    : {
                    'type': 'OpenCL',
                },
                'layers'    : [
                    {'id': 'V1'},
                ],
            },
        ],
    }
    ore = OpenRE(config)
    assert isinstance(ore.domains[0].device, OpenCL)
    assert ore.domains[0].neurons.level.device_data_pointer
    assert ore.domains[0].layers_vector.threshold.device_data_pointer
    domain = ore.domains[0]
    layer = domain.layers[0]
    device = ore.domains[0].device
    # prepare neurons
    layer.neurons_metadata.level[0, 0] = sinapse_max_level
    assert not layer.neurons_metadata.flags[0, 0] & neurons.IS_SPIKED

    layer.neurons_metadata.level[0, 1] = layer.relaxation + 1
    layer.neurons_metadata.flags[0, 1] |= neurons.IS_SPIKED
    assert layer.neurons_metadata.flags[0, 1] | neurons.IS_SPIKED

    layer.neurons_metadata.level[0, 2] = sinapse_max_level
    layer.neurons_metadata.flags[0, 2] |= neurons.IS_DEAD
    layer.neurons_metadata.flags[0, 2] |= neurons.IS_SPIKED

    layer.neurons_metadata.level[0, 3] = sinapse_max_level
    layer.neurons_metadata.flags[0, 3] |= neurons.IS_RECEIVER
    layer.neurons_metadata.flags[0, 3] |= neurons.IS_SPIKED

    layer.neurons_metadata.level[0, 4] = -1

    layer.neurons_metadata.level[0, 5] = -1

    domain.neurons.to_device(device)
    domain.tick()
    domain.neurons.from_device(device)

    # check neurons
    assert layer.neurons_metadata.level[0, 0] == 0
    assert layer.neurons_metadata.flags[0, 0] & neurons.IS_SPIKED
    assert layer.neurons_metadata.spike_tick[0, 0] == 1

    assert layer.neurons_metadata.level[0, 1] == 1
    assert not layer.neurons_metadata.flags[0, 1] & neurons.IS_SPIKED
    assert layer.neurons_metadata.spike_tick[0, 1] == 0

    assert layer.neurons_metadata.level[0, 2] == sinapse_max_level
    assert layer.neurons_metadata.flags[0, 2] & neurons.IS_DEAD
    assert layer.neurons_metadata.flags[0, 2] & neurons.IS_SPIKED

    assert layer.neurons_metadata.level[0, 3] == sinapse_max_level
    assert layer.neurons_metadata.flags[0, 3] & neurons.IS_RECEIVER
    assert not layer.neurons_metadata.flags[0, 3] & neurons.IS_SPIKED

    assert layer.neurons_metadata.level[0, 4] == 0

    assert layer.neurons_metadata.level[0, 5] == 0

    assert layer.total_spikes == 1
    assert domain.total_spikes == 1

    # test kernel
    test_length = 10
    test_kernel = np.zeros((test_length,)).astype(np.int32)
    test_kernel_buf = cl.Buffer(
            device.ctx,
            cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
            hostbuf=test_kernel
        )

    device.program.test_kernel(
        device.queue, (test_length,), None,
        test_kernel_buf,
        np.int32(test_length)
    )
    cl.enqueue_copy(device.queue, test_kernel, test_kernel_buf)
    assert list(test_kernel) == [
        neurons.IS_INHIBITORY,
        neurons.IS_SPIKED,
        neurons.IS_DEAD,
        neurons.IS_TRANSMITTER,
        neurons.IS_RECEIVER,
        test_length,
        1, # 3 & IS_INHIBITORY
        2, # 3 & IS_SPIKED
        0, # 3 & IS_DEAD
        test_length
    ]
