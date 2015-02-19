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
        code = """
#pragma OPENCL EXTENSION cl_khr_global_int32_base_atomics : enable
#pragma OPENCL EXTENSION cl_khr_local_int32_base_atomics : enable
#pragma OPENCL EXTENSION cl_khr_global_int32_extended_atomics : enable
#pragma OPENCL EXTENSION cl_khr_local_int32_extended_atomics : enable
#pragma OPENCL EXTENSION cl_khr_int64_base_atomics : enable
#pragma OPENCL EXTENSION cl_khr_int64_base_atomics : enable

unsigned int constant IS_INHIBITORY = 1<<0;
unsigned int constant IS_SPIKED = 1<<1;
unsigned int constant IS_DEAD = 1<<2;
unsigned int constant IS_TRANSMITTER = 1<<3;
unsigned int constant IS_RECEIVER = 1<<4;

__kernel void tick_neurons() {
    int i = get_global_id(0);
}
__kernel void tick_sinapses() {
    int i = get_global_id(0);
}
        """

        # compile the kernel
        self.program = cl.Program(self.ctx, code).build(
            options="-cl-denorms-are-zero " \
                    "-cl-no-signed-zeros " \
                    "-cl-finite-math-only"
        )


    def tick_neurons(self, domain):
        self.program.tick_neurons(self.queue, (domain.neurons.length,), None)

    def tick_sinapses(self, domain):
        self.program.tick_sinapses(self.queue, (domain.neurons.length,), None)

    def upload(self, data):
        # Do not upload empty buffers
        if not len(data):
            return None
        return cl.Buffer(
            self.ctx,
            cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
            hostbuf=data
        )

    def download(self, data, device_data_pointer):
        if device_data_pointer is None:
            return
        cl.enqueue_copy(self.queue, data, device_data_pointer)

def test_device():
    if cl is None:
        # skip test
        return
    from openre import OpenRE
    from pytest import raises
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

