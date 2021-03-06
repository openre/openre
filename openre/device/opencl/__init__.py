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
from openre.data_types import types, null
from openre import synapses
from openre.templates import create_env
from openre.vector import StandaloneVector


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
        env = create_env()
        source_file_name = config.get('source_file_name', "device/opencl.c")
        self.config['threshold_inc'] = self.config.get('threshold_inc', 10)
        self.config['threshold_dec'] = self.config.get('threshold_dec', 5)
        code = env.get_template(source_file_name).render(
            types=types,
            null=null,
            config=self.config
        )

        # search kernel sources by pattern device/*/templates/device/*.c
        #code = [code]
        #base_dir = os.path.join(os.path.dirname(__file__), '..')
        #for module_name in sorted(
        #    [file_name for file_name in os.listdir(base_dir) \
        #     if os.path.isdir('%s/%s' % (base_dir, file_name)) \
        #        and file_name not in ['opencl'] \
        #        and file_name[0:2] != '__'
        #    ]
        #):
        #    module_dir = os.path.join(base_dir, module_name)
        #    if os.path.isdir(os.path.join(module_dir, 'templates')) \
        #       and os.path.isdir(os.path.join(
        #           module_dir, 'templates', 'device')):
        #        templates_dir = os.path.join(module_dir, 'templates', 'device')
        #        # find *.c
        #        for code_file_name in sorted(
        #            [file_name for file_name in os.listdir(templates_dir) \
        #             if os.path.isfile('%s/%s' % (templates_dir, file_name)) \
        #                and file_name[-2:] == '.c'
        #            ]
        #        ):
        #            code.append(
        #                env.get_template('device/%s' % code_file_name).render(
        #                    types=types,
        #                    null=null
        #                )
        #            )
        #code = ''.join(code)

        # compile the kernel
        self.program = cl.Program(self.ctx, code).build(
            options="-cl-denorms-are-zero " \
                    "-cl-no-signed-zeros " \
                    "-cl-finite-math-only"
        )
        self._source_cache = None


    def tick_neurons(self, domain):
        length = domain.neurons.length
        if not length:
            return
        self.tick_layers_input_data(domain)
        self.program.tick_neurons(
            self.queue, (length,), None,
            # domain
            types.tick(domain.ticks),
            # layers
            domain.layers_vector.threshold.device_data_pointer,
            domain.layers_vector.relaxation.device_data_pointer,
            domain.layers_vector.spike_cost.device_data_pointer,
            domain.layers_vector.max_vitality.device_data_pointer,
            # neurons
            domain.neurons.level.device_data_pointer,
            domain.neurons.flags.device_data_pointer,
            domain.neurons.spike_tick.device_data_pointer,
            domain.neurons.layer.device_data_pointer,
            domain.neurons.vitality.device_data_pointer,
            domain.neurons.threshold.device_data_pointer
        ).wait()
        self.tick_layers_output_data(domain)

    def tick_synapses(self, domain):
        length = domain.neurons.length
        if not length:
            return
        self.program.tick_synapses(
            self.queue, (length,), None,
            # domain
            types.synapse_level(domain.learn_rate),
            types.synapse_level(domain.learn_threshold),
            types.tick(domain.spike_learn_threshold),
            types.tick(domain.spike_forget_threshold),
            # neurons
            domain.neurons.level.device_data_pointer,
            domain.neurons.flags.device_data_pointer,
            domain.neurons.spike_tick.device_data_pointer,
            # synapses
            domain.synapses.level.device_data_pointer,
            domain.synapses.pre.device_data_pointer,
            domain.synapses.post.device_data_pointer,
            domain.synapses.learn.device_data_pointer,
            domain.synapses.flags.device_data_pointer,
            # pre-neuron - synapse index
            domain.pre_synapse_index.key.device_data_pointer,
            domain.pre_synapse_index.value.device_data_pointer,
            # post-neuron - synapse index
            domain.post_synapse_index.key.device_data_pointer,
            domain.post_synapse_index.value.device_data_pointer
        ).wait()
        # download layers stats from device once
        # per domain.config['stat_size'] ticks
        if  domain.ticks % domain.config['stat_size'] == 0:
            domain.stat_vector.data.fill(0)
            self.program.update_layers_stat(
                self.queue, (domain.neurons.length,), None,
                # domain
                types.tick(domain.ticks),
                types.address(domain.config['stat_size']),
                types.address(domain.stat_fields),
                # layers
                domain.layers_stat.device_data_pointer,
                domain.layers_vector.max_vitality.device_data_pointer,
                # neurons
                domain.neurons.flags.device_data_pointer,
                domain.neurons.spike_tick.device_data_pointer,
                domain.neurons.layer.device_data_pointer,
                domain.neurons.vitality.device_data_pointer
            ).wait()
            domain.layers_stat.from_device(self)
            stat_length = len(domain.stat_vector)
            for layer_address in range(len(domain.layers)):
                layer_stat_start = \
                        domain.stat_fields \
                        * layer_address
                domain.stat_vector.data += domain.layers_stat.data[
                    layer_stat_start : layer_stat_start + stat_length
                ]
            self.program.init_layers_stat(
                self.queue, (len(domain.layers_stat),), None,
                domain.layers_stat.device_data_pointer
            ).wait()
            if len(domain.synapses):
                # count synapses stats
                domain.stat_vector.to_device(self)
                self.program.update_synapses_stat(
                    self.queue, (len(domain.synapses),), None,
                    domain.stat_vector.device_data_pointer,
                    # synapses
                    domain.synapses.learn.device_data_pointer,
                    domain.synapses.flags.device_data_pointer
                ).wait()
                domain.stat_vector.from_device(self)
            domain.stat_set('stat_size', domain.config['stat_size'])
            # 0 - total spikes (one per neuron) per self.config['stat_size']
            # ticks
            domain.stat_set('total_spikes', domain.stat_vector.data[0])
            # 1 - number of the dead neurons
            domain.stat_set('dead_neurons', domain.stat_vector.data[1])
            # 2 - number of synapses with flag IS_STRENGTHENED
            domain.stat_set('strengthened_synapses', domain.stat_vector.data[2])
            # 3 - neurons tiredness = sum(layer.max_vitality - neuron.vitality)
            domain.stat_set('neurons_tiredness', domain.stat_vector.data[3])
            # 4 - synapse learn level
            domain.stat_set('synapse_learn_level', domain.stat_vector.data[4])

    def tick_transmitter_index(self, domain):
        length = len(domain.transmitter_index.local_address)
        if not length:
            return
        self.program.tick_transmitter_index(
            self.queue, (length,), None,
            # transmitter_index
            domain.transmitter_index.local_address.device_data_pointer,
            domain.transmitter_index.is_spiked.device_data_pointer,
            # neurons
            domain.neurons.flags.device_data_pointer,
        ).wait()

    def tick_receiver_index(self, domain):
        length = len(domain.receiver_index.local_address)
        if not length:
            return
        self.program.tick_receiver_index(
            self.queue, (length,), None,
            # transmitter_index
            domain.receiver_index.local_address.device_data_pointer,
            domain.receiver_index.is_spiked.device_data_pointer,
            # neurons
            domain.neurons.flags.device_data_pointer,
        ).wait()

    def tick_layers_input_data(self, domain):
        """
        Add value from layer.input_data to neurons.level
        """
        ticks = domain.ticks
        for layer in domain.layers:
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
                    "Domain '%s': len(input_data_vector)=%s, layer.length=%s" \
                    % (domain.name, len(input_data_vector), layer.length)
                layer.input_data_cache = input_data_vector
            length = len(input_data_vector)
            if not length:
                return
            input_data_vector.to_device(self)
            # only one layer with the same dims as input data
            assert length == len(layer.neurons_metadata.level)
            self.program.tick_numpy_input_data_uint8(
                self.queue, (length,), None,
                # data
                input_data_vector.device_data_pointer,
                # layer
                types.address(layer.neurons_metadata.address),
                # neurons
                domain.neurons.level.device_data_pointer
            ).wait()
            if layer.input_expire <= ticks:
                layer.input_data = None
                layer.input_data_cache = None

    def tick_layers_output_data(self, domain):
        """
        Convert layer ticks to numpy array
        (if layer.config.get('output') is True)
        """
        length = len(domain.output_index.address)
        if not length:
            return
        output_index = domain.output_index
        self.program.tick_numpy_output_data_uint8(
            self.queue, (length,), None,
            # domain
            types.tick(domain.ticks),
            # output index
            output_index.address.device_data_pointer,
            output_index.data.device_data_pointer,
            output_index.tick.device_data_pointer,
            # neurons
            domain.neurons.flags.device_data_pointer
        ).wait()
        # find all source consumers and cache it
        if self._source_cache is None:
            self._source_cache = {}
            cache = self._source_cache
            for layer in domain.layers:
                if 'output' not in layer.config:
                    continue
                source_id = layer.config['output']
                cache[source_id] = []
            net = domain.net
            # consumers
            for other_domain in net.domains:
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

        domain.neurons.flags.from_device(self)
        output_index.data.from_device(self)
        cache = self._source_cache
        for source_id, data in output_index.data_to_send():
            for consumer_domain, layer_index in cache[source_id]:
                consumer_domain.register_input_layer_data(layer_index, data)


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

class IOBaseTesterSimpleCheck(OpenCL):
    def tick_layers_input_data(self, domain):
        import numpy as np
        for layer_index, layer in enumerate(domain.layers):
            if not layer.input_data:
                continue
            input_data_vector = StandaloneVector()
            data = layer.input_data
            if isinstance(data, basestring):
                input_data_vector.from_bytes(data)
            else:
                input_data_vector.set_data(data)
            check = np.zeros(40, dtype=np.uint8)
            check.fill(layer_index)
            assert list(input_data_vector.data) == list(check)
            domain.stat_inc('test_io_input')
        ret = super(IOBaseTesterSimpleCheck,
                     self).tick_layers_input_data(domain)
        assert layer.input_data is None
        return ret

def test_device():
    if cl is None:
        # skip test
        return
    from openre import OpenRE
    import numpy as np
    from openre import neurons
    synapse_max_level = 30000
    config = {
        'synapse': {
            'max_level': synapse_max_level,
            'spike_learn_threshold': 2,
        },
        'layers': [
            {
                'name': 'V1',
                'threshold': synapse_max_level,
                'relaxation': 1000,
                'width': 20,
                'height': 20,
                'is_inhibitory': True,
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
                'threshold': synapse_max_level,
                'relaxation': 1000,
                'width': 20,
                'height': 20,
            },
        ],
        'domains': [
            {
                'name'        : 'D1',
                'device'    : {
                    'type': 'OpenCL',
                    'threshold_inc': 0,
                    'threshold_dec': 0
                },
                'stat_size': 1,
                'layers'    : [
                    {'name': 'V1'},
                    {'name': 'V2'},
                ],
            },
        ],
    }
    ore = OpenRE(config)
    ore.deploy()
    assert isinstance(ore.domains[0].device, OpenCL)
    assert ore.domains[0].neurons.level.device_data_pointer
    assert ore.domains[0].layers_vector.threshold.device_data_pointer
    domain = ore.domains[0]
    layer = domain.layers[0]
    layer2 = domain.layers[1]
    device = ore.domains[0].device
    max_vitality = types.max(types.vitality)

    # check lengths
    assert len(domain.synapses.level) == 400
    assert len(domain.synapses) == 400
    assert domain.neurons.length == 800
    assert layer.neurons_metadata.threshold[0] == synapse_max_level
    assert layer.neurons_metadata.level.length == 400
    assert layer2.neurons_metadata.level.length == 400
    for field, field_type in domain.synapses_metadata.__class__.fields:
        assert getattr(domain.synapses_metadata, field).length == 400
        assert len(getattr(domain.synapses, field).data) == 400
    assert domain.pre_synapse_index.key.length == 800
    assert domain.pre_synapse_index.value.length == 400

    assert domain.post_synapse_index.key.length == 800
    assert domain.post_synapse_index.value.length == 400

    # prepare neurons
    layer.neurons_metadata.level[0, 0] = synapse_max_level
    assert not layer.neurons_metadata.flags[0, 0] & neurons.IS_SPIKED

    layer.neurons_metadata.level[0, 1] = layer.relaxation + 1
    layer.neurons_metadata.flags[0, 1] |= neurons.IS_SPIKED
    assert layer.neurons_metadata.flags[0, 1] | neurons.IS_SPIKED

    layer.neurons_metadata.level[0, 2] = synapse_max_level
    layer.neurons_metadata.flags[0, 2] |= neurons.IS_DEAD
    layer.neurons_metadata.flags[0, 2] |= neurons.IS_SPIKED

    layer.neurons_metadata.level[0, 3] = synapse_max_level
    layer.neurons_metadata.flags[0, 3] |= neurons.IS_RECEIVER
    layer.neurons_metadata.flags[0, 3] |= neurons.IS_SPIKED

    layer.neurons_metadata.level[0, 4] = -1

    layer.neurons_metadata.level[0, 5] = -1

    layer.neurons_metadata.level[0, 6] = synapse_max_level
    layer.neurons_metadata.vitality[0, 6] = layer.spike_cost

    layer.neurons_metadata.level[0, 7] = synapse_max_level
    layer2.neurons_metadata.level[0, 7] = synapse_max_level

    # synapses
    before = layer2.neurons_metadata.level[0, 0]
    synapse_address = domain.pre_synapse_index.key[0]
    synapse_level = domain.synapses.level[synapse_address]
    layer.neurons_metadata.level[1, 0] = synapse_max_level
    layer2.neurons_metadata.flags[1, 0] |= neurons.IS_DEAD
    layer2.neurons_metadata.level[1, 1] = synapse_max_level
    layer.neurons_metadata.flags[1, 2] |= neurons.IS_DEAD
    layer2.neurons_metadata.level[1, 2] = synapse_max_level

    l2_n_level_before = layer2.neurons_metadata.level[0, 0]

    layer2.neurons_metadata.level[0, 6] = synapse_max_level
    s_level_before_7 = domain.synapses.level[domain.post_synapse_index.key[
        layer2.neurons_metadata.level.to_address(0, 7)
    ]]
    domain.synapses.learn[domain.post_synapse_index.key[
        layer2.neurons_metadata.level.to_address(0, 7)
    ]] = domain.learn_threshold

    domain.neurons.to_device(device)
    domain.synapses.to_device(device)
    domain.tick()
    domain.neurons.from_device(device)
    domain.synapses.from_device(device)
    s_level = domain.synapses.level[domain.post_synapse_index.key[
        layer2.neurons_metadata.level.to_address(0, 0)
    ]]
    if l2_n_level_before - layer2.relaxation < 0:
        res = np.int32(0) - s_level
        assert res == layer2.neurons_metadata.level[0, 0]
    else:
        assert l2_n_level_before - s_level - layer2.relaxation \
                == layer2.neurons_metadata.level[0, 0]

    # check neurons (layer.neurons_metadata.level[x, y])
    assert layer.neurons_metadata.level[0, 0] == 0
    assert layer.neurons_metadata.flags[0, 0] & neurons.IS_SPIKED
    assert layer.neurons_metadata.spike_tick[0, 0] == 1
    assert layer.neurons_metadata.vitality[0, 0] \
            == max_vitality - layer.spike_cost + 1

    assert layer.neurons_metadata.level[0, 1] == 1
    assert not layer.neurons_metadata.flags[0, 1] & neurons.IS_SPIKED
    assert layer.neurons_metadata.spike_tick[0, 1] == 0
    assert layer.neurons_metadata.vitality[0, 1] \
            == max_vitality

    assert layer.neurons_metadata.level[0, 2] == synapse_max_level
    assert layer.neurons_metadata.flags[0, 2] & neurons.IS_DEAD
    assert layer.neurons_metadata.flags[0, 2] & neurons.IS_SPIKED

    assert layer.neurons_metadata.level[0, 3] == synapse_max_level
    assert layer.neurons_metadata.flags[0, 3] & neurons.IS_RECEIVER
    assert not layer.neurons_metadata.flags[0, 3] & neurons.IS_SPIKED

    assert layer.neurons_metadata.level[0, 4] == 0

    assert layer.neurons_metadata.level[0, 5] == 0

    # spike and dies (low neuron.vitality)
    assert not layer.neurons_metadata.flags[0, 6] & neurons.IS_SPIKED
    assert layer.neurons_metadata.flags[0, 6] & neurons.IS_DEAD
    assert layer.neurons_metadata.vitality[0, 6] \
            == max_vitality

    # check synapses
    s_level_after_7 = domain.synapses.level[domain.post_synapse_index.key[
        layer2.neurons_metadata.level.to_address(0, 7)
    ]]
    s_learn_after_7 = domain.synapses.learn[domain.post_synapse_index.key[
        layer2.neurons_metadata.level.to_address(0, 7)
    ]]
    #assert s_level_before_7 == s_level_after_7
    assert domain.synapses.flags[domain.post_synapse_index.key[
        layer2.neurons_metadata.level.to_address(0, 7)
    ]] & synapses.IS_STRENGTHENED
    assert not domain.synapses.flags[domain.post_synapse_index.key[
        layer2.neurons_metadata.level.to_address(0, 0)
    ]] & synapses.IS_STRENGTHENED

    before = before - 1000
    if before < 0:
        before = 0
    # layer 1 is inhibitory
    assert layer2.neurons_metadata.level[0, 0] == before - synapse_level
    # dead post-neuron so synapse level should be 0
    assert domain.synapses.level[domain.pre_synapse_index.key[
        layer.neurons_metadata.level.to_address(1, 0)
    ]] == 0
    assert layer2.neurons_metadata.flags[1, 1] & neurons.IS_SPIKED
    # dead pre-neuron so synapse level should be 0
    assert domain.synapses.level[domain.post_synapse_index.key[
        layer2.neurons_metadata.level.to_address(1, 2)
    ]] == 0
    assert domain.synapses.learn[domain.pre_synapse_index.key[
        layer.neurons_metadata.level.to_address(0, 0)
    ]] == 0
    # check stats
    for field_num in range(0, domain.stat_fields):
        if field_num not in [2, 4]:
            assert domain.stat_vector[0 + field_num] \
                == domain.layers_stat[0 + field_num] \
                + domain.layers_stat[ \
                    0 + field_num + len(domain.stat_vector)]

    assert domain.config['stat_size'] == domain.stat('stat_size')
    # field 0 - total spikes
    assert domain.stat_vector[0] >= 4
    assert domain.stat_vector[0] == domain.stat('total_spikes')
    assert domain.layers_stat[0] >= 2
    assert domain.layers_stat[0 + len(domain.stat_vector)] >= 2
    # field 1 - number of the dead neurons
    assert domain.layers_stat[1] == 3
    assert domain.stat_vector[1] == domain.stat('dead_neurons')
    assert domain.layers_stat[1 + len(domain.stat_vector)] == 1
    # field 2 - number of synapses with IS_STRENGTHENED flag
    assert domain.stat_vector[2] == 1
    assert domain.stat_vector[2] == domain.stat('strengthened_synapses')
    # field 3 - tiredness
    assert domain.layers_stat[3] \
            == (layer.spike_cost - 1) * domain.layers_stat[0]
    assert domain.layers_stat[3 + len(domain.stat_vector)] \
            == (layer2.spike_cost - 1) \
                * domain.layers_stat[0 + len(domain.stat_vector)]
    assert domain.stat_vector[3] == domain.stat('neurons_tiredness')
    # field 4 - sum(synapse.learn)
    assert domain.stat_vector[4] >= (domain.learn_rate - 1)
    assert domain.stat_vector[4] == domain.stat('synapse_learn_level')

    # test kernel
    test_length = 16
    test_kernel = np.zeros((test_length,)).astype(np.uint32)
    test_kernel_buf = cl.Buffer(
            device.ctx,
            cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
            hostbuf=test_kernel
        )

    device.program.test_kernel(
        device.queue, (test_length,), None,
        test_kernel_buf,
        np.int32(test_length),
        np.uint32(types.max(types.vitality))
    )
    cl.enqueue_copy(device.queue, test_kernel, test_kernel_buf)
    assert 8 | (3 & neurons.IS_SPIKED) == 10
    assert 8 | (1 & neurons.IS_SPIKED) == 8
    assert 7 & ~neurons.IS_SPIKED == 5
    assert 8 & ~neurons.IS_SPIKED == 8
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
        test_length,
        null,
        synapses.IS_STRENGTHENED,
        3,
        8 | (3 & neurons.IS_SPIKED),
        7 & ~neurons.IS_SPIKED,
        types.max(types.vitality),
    ]


    # remote domains
    config = {
        'synapse': {
            'max_level': synapse_max_level,
            'spike_learn_threshold': 2,
        },
        'layers': [
            {
                'name': 'V1',
                'threshold': synapse_max_level,
                'relaxation': 1000,
                'width': 20,
                'height': 20,
                'is_inhibitory': True,
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
                'threshold': synapse_max_level,
                'relaxation': 1000,
                'width': 20,
                'height': 20,
            },
        ],
        'domains': [
            {
                'name'        : 'D1',
                'device'    : {
                    'type': 'OpenCL',
                },
                'layers'    : [
                    {'name': 'V1'},
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
    d1 = ore.domains[0]
    d2 = ore.domains[1]
    v1 = d1.layers[0]
    v1.neurons_metadata.level[0, 0] = synapse_max_level
    d1.neurons.to_device(d1.device)
    d1.synapses.to_device(d1.device)
    d1.tick()
    d1.neurons.from_device(d1.device)
    d1.synapses.from_device(d1.device)
    d1.transmitter_index.is_spiked.from_device(d1.device)
    assert v1.neurons_metadata.flags[0, 0] & neurons.IS_SPIKED
    assert v1.neurons_metadata.flags[0, 0] & neurons.IS_INHIBITORY
    assert d1.transmitter_index.is_spiked[0]
    #assert d1.transmitter_index.flags[0] & neurons.IS_INHIBITORY

    assert d2.receiver_index.is_spiked[0]
    local_address = d2.receiver_index.local_address[0]
    assert local_address == 400
    assert not d2.neurons.flags[local_address] & neurons.IS_SPIKED
    assert d2.neurons.flags[local_address] & neurons.IS_INHIBITORY
    assert d2.neurons.flags[local_address] & neurons.IS_RECEIVER
    d2.tick()
    d2.neurons.from_device(d2.device)
    assert not d2.receiver_index.is_spiked[0]
    assert d2.neurons.flags[local_address] & neurons.IS_SPIKED
    assert d2.neurons.flags[local_address] & neurons.IS_INHIBITORY
    assert d2.neurons.flags[local_address] & neurons.IS_RECEIVER


def test_input():
    for expire in range(3):
        check_input(expire)

def check_input(expire):
    import numpy
    from openre import OpenRE
    from openre.vector import StandaloneVector
    from openre import neurons
    import logging
    # remote domains
    config = {
        'layers': [
            {
                'name': 'Input',
                'width': 10,
                'height': 10,
                'is_inhibitory': False,
                'threshold': 128,
                'relaxation': 0,
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
                'relaxation': 0,
            },
        ],
        'domains': [
            {
                'name'        : 'D1',
                'device'    : {
                    'type': 'OpenCL',
                    'threshold_inc': 0,
                    'threshold_dec': 0
                },
                'layers'    : [
                    {'name': 'Input', 'shape': [0, 0, 5, 5], 'expire': expire},
                    {'name': 'Input', 'shape': [0, 5, 5, 5], 'expire': expire},
                    {'name': 'Input', 'shape': [5, 0, 5, 5], 'expire': expire},
                    {'name': 'Input', 'shape': [5, 5, 5, 5], 'expire': expire},
                ],
            },
            {
                'name'        : 'D2',
                'device'    : {
                    'type': 'OpenCL',
                    'threshold_inc': 0,
                    'threshold_dec': 0
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

    #arr = StandaloneVector(numpy.reshape(arr, (10, 10)))
    arr = numpy.reshape(arr, (10, 10))
    l0 = arr[0:5, 0:5]
    l1 = arr[5:10, 0:5]
    l2 = arr[0:5, 5:10]
    l3 = arr[5:10, 5:10]
    # somewhere here we will send packet to the input device
    # and in input device will receive it:
    layer_data = [l0, l1, l2, l3]
    for layer_index, data in enumerate(layer_data):
        if layer_index % 2:
            D1.register_input_layer_data(
                layer_index,
                StandaloneVector(data).bytes()
            )
        else:
            D1.register_input_layer_data(
                layer_index,
                data
            )
    neurons_length = 0
    for layer_index, data in enumerate(layer_data):
        layer = D1.layers[layer_index]
        vector = StandaloneVector()
        if isinstance(layer.input_data, basestring):
            vector.from_bytes(layer.input_data)
        else:
            vector.set_data(layer.input_data)
        assert list(vector.data) == list(numpy.ravel(data))
        assert len(vector.data) == len(numpy.ravel(data))
        neurons_length += len(vector.data)
    assert len(D1.neurons.level) == neurons_length
    D1.neurons.level.data[:] = 0
    D1.neurons.level.to_device(device1)
    D2.neurons.level.data[:] = 0
    D2.neurons.level.to_device(device2)
    ore.tick()
    D1.neurons.from_device(device1)
    D2.neurons.from_device(device2)
    level_check \
            = numpy.ravel(numpy.concatenate(layer_data)).astype(numpy.uint32)
    level_check[level_check >= 128] -= 128
    assert list(D1.neurons.level.data) == list(level_check)
    flags_check = numpy.ravel(numpy.concatenate(layer_data))
    flags_check[flags_check < 128] = neurons.IS_TRANSMITTER
    flags_check[flags_check >= 128] = neurons.IS_TRANSMITTER | neurons.IS_SPIKED
    assert list(flags_check) == list(D1.neurons.flags.data)
    # check D2 neuron level
    flags2_check = numpy.ravel(numpy.concatenate(layer_data))
    level2_check = numpy.copy(D2.synapses.level.data)
    level2_check[flags2_check < 128] = 0
    neurons2_level = numpy.reshape(
        D2.neurons.level.data[0:len(level2_check)],
        (10, 10)
    )
    l20 = neurons2_level[0:5, 0:5]
    l21 = neurons2_level[5:10, 0:5]
    l22 = neurons2_level[0:5, 5:10]
    l23 = neurons2_level[5:10, 5:10]
    layer2_data = [l20, l21, l22, l23]
    # D2 neuron level should be eq to synapses levels
    assert list(numpy.ravel(numpy.concatenate(layer2_data))) \
            == list(level2_check)
    try:
        for pass_num in range(2, 4):
            ore.tick()
            D1.neurons.from_device(device1)
            D2.neurons.from_device(device2)
            if expire and expire >= pass_num:
                level_check = level_check \
                        + numpy.ravel(numpy.concatenate(layer_data))
            level_check[level_check >= 128] -= 128
            assert list(D1.neurons.level.data) == list(level_check)
            if not expire or expire < pass_num:
                for layer_index, data in enumerate(layer_data):
                    assert layer.input_data_cache is None
                    assert layer.input_data is None
    except AssertionError:
        logging.warn('Expire #%s, pass #%s', expire, pass_num)
        raise

def test_output():
    from openre import OpenRE
    config = {
        'layers': [
            {
                'name': 'V1',
                'relaxation': 0,
                'width': 16,
                'height': 10,
            },
            {
                'name': 'V2',
                'relaxation': 0,
                'width': 16,
                'height': 10,
            },
        ],
        'domains': [
            {
                'name'        : 'D1',
                'device'    : {
                    'type': 'OpenCL',
                },
                'layers'    : [
                    {'name': 'V2', 'output': 'o1', 'shape': [0, 0, 8, 5]},
                    {'name': 'V2', 'output': 'o2', 'shape': [8, 0, 8, 5]},
                    {'name': 'V2', 'output': 'o3', 'shape': [0, 5, 8, 5]},
                    {'name': 'V2', 'output': 'o4', 'shape': [8, 5, 8, 5]},
                ],
            },
            {
                'name'        : 'D2',
                'device'    : {
                    'type': 'OpenCL',
                },
                'layers'    : [
                    {'name': 'V1', 'input': 'o1', 'shape': [0, 0, 8, 5]},
                    {'name': 'V1', 'input': 'o2', 'shape': [8, 0, 8, 5]},
                    {'name': 'V1', 'input': 'o3', 'shape': [0, 5, 8, 5]},
                    {'name': 'V1', 'input': 'o4', 'shape': [8, 5, 8, 5]},
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
    D1.neurons.level.data[0] = 35000
    D2.neurons.level.data[:] = 0
    D1.neurons.level.to_device(device1)
    D2.neurons.level.to_device(device2)
    ore.tick()
    D1.neurons.from_device(device1)
    D2.neurons.from_device(device2)
    assert D2.neurons.level.data[0] == 255
    D1.neurons.level.data[1] = 35000
    D1.neurons.level.to_device(device1)
    ore.tick()
    D1.neurons.from_device(device1)
    D2.neurons.from_device(device2)
    assert D2.neurons.level.data[0] == 255 + 254
    assert D2.neurons.level.data[1] == 254
