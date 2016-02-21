# -*- coding: utf-8 -*-
"""
Содержит в себе слои и синапсы. Запускается в текущем процессе.
"""
from openre.domain.base import DomainBase
from openre.vector import Vector
from openre.metadata import Metadata
from types import GeneratorType
from openre.data_types import types
from openre.layer import Layer, LayersVector
from openre.neurons import NeuronsVector, IS_TRANSMITTER, create_neuron, \
        NeuronsExtendableMetadata, IS_RECEIVER, IS_SPIKED, IS_DEAD
from openre.synapses import SynapsesVector, SynapsesMetadata
import logging
import uuid
import random
from copy import deepcopy
import math
from openre.index import SynapsesIndex, TransmitterIndex, ReceiverIndex, \
        OutputIndex
from openre import device
import numpy as np
from openre.domain.packets import TransmitterVector, ReceiverVector, \
        SpikesVector
from openre.domain.remote import RemoteDomainBase
import time
import datetime


class Domain(DomainBase):
    """
    Домен (Domain) - содержит один и более слоев состоящих из нейронов,
    связанных друг с другом синапсами. Домен можно воспринимать как один процесс
    в операционной системе, реализующий частично или полностью какой либо
    функционал. В некоторых случаях домен может не содержать синапсов (например,
    если домен является источником данных с сенсоров)

    self.name: types.address - должен быть уникальным для всех доменов
    self.ticks: types.tick - номер тика с момента запуска. При 32 битах и 1000
                             тиков в секунду переполнение произойдет через 49
                             дней. При 64 битах через 584 млн. лет.
    self.spike_learn_threshold: types.tick - как близко друг к другу по времени
                                должен сработать pre и post нейрон, что бы
                                поменялся вес синапса в большую сторону.
                                0 - по умолчанию (сеть не обучается).
    self.spike_forget_threshold: types.tick - насколько сильной должна быть
                                 разница между pre.tick и post.tick что бы
                                 уменьшился вес синапса.
                                 0 - по умолчанию (сеть не забывает).
    self.layers - список слоев (class Layer) домена
    self.learn_rate: types.synapse_level - с какой скоростью увеличивается
                     synapse.learn если у нейронов синапса расстояние между
                     спайками меньше чем self.spike_learn_threshold
    self.learn_threshold: types.synapse_level - какой максимальный уровень может
                          быть у synapse.learn. При спайке synapse.learn
                          суммируется с synapse.level (кратковременная память)
                          и суммарный сигнал передается post-нейрону.
                          Минимальный уровень у synapse.learn == 0. При первом
                          достижении максимального уровня синапс должен
                          одноразово усиливаться (долговременная память).
    Жеательно что бы выполнялось условие:
        0 <= spike_learn_threshold <= spike_forget_threshold <= types.tick.max
    """
    def __init__(self, config, net, domain_index):
        super(Domain, self).__init__(config, net, domain_index)

        self.ticks = 0
        self.synapse_count_by_domain = {}
        self.spike_learn_threshold \
                = self.net.config['synapse'].get('spike_learn_threshold', 0)
        self.spike_forget_threshold \
                = self.net.config['synapse'].get('spike_forget_threshold', 0)
        self.learn_rate \
                = self.net.config['synapse'].get('learn_rate', 0)
        self.learn_threshold \
                = self.net.config['synapse'].get('learn_threshold', 0)
        self.layers = []
        self.layers_vector = LayersVector()
        # domain layers config
        self.layers_config = deepcopy(self.config['layers'])
        # neurons vector. Metadata stored in layer.neurons_metadata
        self.neurons = NeuronsVector()
        self.remote_neuron_address = -1
        self.remote_neurons_metadata = NeuronsExtendableMetadata(0)

        # synapses vector
        self.synapse_address = -1
        self.synapses = SynapsesVector(
            0, self.net.config['synapse']['max_level'])
        self.synapses_metadata = None
        self.random = random.Random()
        self.seed = uuid.uuid4().hex
        self.pre_synapse_index = None
        self.post_synapse_index = None
        self.device = getattr(
            device,
            self.config['device'].get('type', 'OpenCL')
        )(self.config['device'])
        self.cache = {}
        # stats for domain (number of spikes)
        self.stat_vector = Vector()
        # fields:
        # 0 - total spikes (one per neuron) per self.config['stat_size'] ticks
        # 1 - number of the dead neurons
        # 2 - number of synapses with flag IS_STRENGTHENED
        # 3 - neurons tiredness = sum(layer.max_vitality - neuron.vitality)
        # 4 - synapse learn level
        self.stat_fields = 5
        stat_metadata = Metadata(
            (1, self.stat_fields),
            types.stat
        )
        self.stat_vector.add(stat_metadata)
        # stats for vectors
        self.layers_stat = Vector()

        self.transmitter_index = TransmitterIndex()
        self.receiver_index = ReceiverIndex()

        self.output_index = OutputIndex()

        logging.debug('Domain created (name: %s)', self.name)

    def deploy_layers(self):
        """
        Create layers
        """
        logging.debug('Deploy domain (name: %s)', self.name)
        for layer_config in self.layers_config:
            layer = Layer(layer_config)
            self.neurons.add(layer.neurons_metadata)
            layer.address = layer.neurons_metadata.address
            self.layers.append(layer)
            layer_config['layer'] = layer
            self.layers_vector.add(layer.layer_metadata)
            layer_stat_metadata = Metadata(
                (1, self.stat_fields),
                types.stat
            )
            self.layers_stat.add(layer_stat_metadata)
        self.neurons.add(self.remote_neurons_metadata)
        for layer_config in self.layers_config:
            for connect in layer_config.get('connect', []):
                connect['domain_layers'] = []
            for layer in self.layers:
                for connect in layer_config.get('connect', []):
                    if connect['name'] == layer.name:
                        connect['domain_layers'].append(layer)
        logging.debug('Allocate layers vector')
        for layer_name, layer in enumerate(self.layers):
            self.layers_vector.threshold[layer_name] = layer.threshold
            self.layers_vector.relaxation[layer_name] = layer.relaxation
            self.layers_vector.spike_cost[layer_name] = layer.spike_cost
            self.layers_vector.max_vitality[layer_name] = layer.max_vitality

    def deploy_neurons(self):
        """
        Create neurons
        """
        logging.debug(
            'Total %s local neurons in domain',
            len(self.neurons)
        )
        self.create_neurons()

    def pre_deploy_synapses(self):
        """
        Init synapses vector
        """
        # allocate synapses buffer in memory
        self.synapses_metadata = SynapsesMetadata(0)
        self.synapses.add(self.synapses_metadata)

    def deploy_synapses_async(self):
        """
        Async version of deploy_synapses
        """
        ret = self.create_synapses()
        # Create synapses
        if isinstance(ret, GeneratorType):
            for res in ret:
                yield res

        domain_total_synapses = self.synapse_count_by_domain.get(self.name, 0)
        if not domain_total_synapses:
            logging.warn('No synapses in domain %s', self.name)
        logging.debug(
            'Total %s local synapses in domain',
            domain_total_synapses
        )

    def deploy_synapses(self):
        """
        Create synapses
        """
        list(self.deploy_synapses_async())

    def post_deploy_synapses(self):
        """
        Run after all domains is synced
        """
        # sync length between synapses multifield metadata fields
        self.synapses_metadata.sync_length(self.synapse_address+1)
        # sync self.neurons length after adding remote neurons
        self.remote_neurons_metadata.sync_length(self.remote_neuron_address+1)
        logging.debug(
            'Total %s neurons in domain %s',
            len(self.neurons),
            self.name
        )
        logging.debug(
            'Total %s synapses in domain %s',
            len(self.synapses),
            self.name
        )

    def deploy_indexes(self):
        """
        Create indexes
        """
        # create pre-neuron - synapse index
        logging.debug('Create pre-neuron - synapse index')
        self.pre_synapse_index = SynapsesIndex(
            len(self.neurons), self.synapses.pre)
        # create post-neuron - synapse index
        logging.debug('Create post-neuron - synapse index')
        self.post_synapse_index = SynapsesIndex(
            len(self.neurons), self.synapses.post)
        self.transmitter_index.shrink()
        self.receiver_index.shrink()
        logging.debug('Create output indexes')
        for layer in self.layers:
            self.output_index.add(layer)
        self.output_index.shrink()


    def deploy_device(self):
        """
        Upload data to device
        """
        logging.debug('Upload data to device')
        for vector in [
            self.layers_vector,
            self.neurons,
            self.synapses,
            self.pre_synapse_index,
            self.post_synapse_index,
            self.stat_vector,
            self.layers_stat,
            self.transmitter_index,
            self.receiver_index,
            self.output_index,
        ]:
            vector.create_device_data_pointer(self.device)
        logging.debug('Domain deployed (name: %s)', self.name)

    def create_synapses(self):
        """
        Создаем физически синапсы
        """
        logging.debug('Create synapses')
        # Domains synapses
        return self.connect_layers()

    def connect_layers(self):
        """
        Реализует непосредственное соединение слоев
        """
        self.random.seed(self.seed)
        layer_config_by_name = {}
        total_synapses = self.synapse_count_by_domain
        # cache
        self_connect_neurons = self.connect_neurons
        for layer_config in self.net.config['layers']:
            layer_config_by_name[layer_config['name']] = layer_config
        domain_index_to_name = []
        for domain_index, domain in enumerate(self.net.config['domains']):
            domain_index_to_name.append(domain['name'])
            total_synapses[domain['name']] = 0
            if domain['name'] == self.name:
                pre_domain_index = domain_index
        # cache neuron -> domain and neuron -> layer in domain
        if 'layer' not in self.cache:
            self.cache['layer'] = {}
            for layer_config in self.net.config['layers']:
                # heihgt x width x z,
                # where z == 0 is domain index in net and
                #       z == 1 is layer index in domain
                self.cache['layer'][layer_config['name']] = \
                    np.zeros(
                        (layer_config['height'], layer_config['width'], 2),
                        dtype=np.int
                    )
                self.cache['layer'][layer_config['name']] \
                        .fill(np.iinfo(np.int).max)
            for domain_index, domain in enumerate(self.net.config['domains']):
                layer_index = -1
                for layer in domain['layers']:
                    layer_index += 1
                    layer = deepcopy(layer)
                    layer_config = layer_config_by_name[layer['name']]
                    shape = layer.get(
                        'shape',
                        [0, 0, layer_config['width'], layer_config['height']]
                    )
                    if shape[0] < 0:
                        shape[0] = 0
                    if shape[1] < 0:
                        shape[1] = 0
                    if shape[0] + shape[2] > layer_config['width']:
                        shape[2] = layer_config['width'] - shape[0]
                    if shape[1] + shape[3] > layer_config['height']:
                        shape[3] = layer_config['height'] - shape[1]
                    layer_cache = \
                            self.cache['layer'][layer_config['name']]
                    for y in xrange(shape[1], shape[1] + shape[3]):
                        layer_cache_y = layer_cache[y]
                        for x in xrange(shape[0], shape[0] + shape[2]):
                            layer_cache_y[x][0] = domain_index
                            layer_cache_y[x][1] = layer_index

        # start connecting
        pre_layer_index = -1
        async_time = time.time()
        for layer_config in self.layers_config:
            pre_layer_index += 1
            # no connections with other layers
            if not layer_config.get('connect'):
                continue
            # pre layer. Connect only neurons in this domain
            layer = layer_config['layer']
            # precache method
            layer_to_address = layer.neurons_metadata.level.to_address
            for connect in layer_config.get('connect', []):
                shift = connect.get('shift', [0, 0])
                if callable(shift[0]):
                    def shift_x():
                        return shift[0](self.random)
                else:
                    def shift_x():
                        return shift[0]
                if callable(shift[1]):
                    def shift_y():
                        return shift[1](self.random)
                else:
                    def shift_y():
                        return shift[1]

                post_layer_config = layer_config_by_name[connect['name']]
                post_info_cache = self.cache['layer'][post_layer_config['name']]
                radius = connect.get('radius', max(
                    int(1.0 * layer_config['width'] \
                        / post_layer_config['width'] / 2),
                    int(1.0 * layer_config['height'] \
                        / post_layer_config['height'] / 2)
                ) + 1)
                def pre_layer_coords():
                    for pre_y in xrange(layer.y, layer.y + layer.height):
                        for pre_x in xrange(layer.x, layer.x + layer.width):
                            yield pre_y, pre_x
                for pre_y, pre_x in pre_layer_coords():
                    # Determine post x coordinate of neuron in post layer.
                    # Should be recalculated for every y because of possible
                    # random shift
                    if time.time() - async_time > 0.1:
                        async_time = time.time()
                        yield (pre_y, layer.width)
                    pre_neuron_address = layer_to_address(
                        pre_x - layer.x,
                        pre_y - layer.y
                    )
                    central_post_x = int(math.floor(
                        1.0 * pre_x / (layer_config['width']) \
                        * (post_layer_config['width'])
                        + (post_layer_config['width'] \
                           / layer_config['width'] / 2.0)
                    )) + shift_x()
                    # determine post y coordinate of neuron in post layer
                    central_post_y = int(math.floor(
                        1.0 * pre_y / (layer_config['height']) \
                        * (post_layer_config['height'])
                        + (post_layer_config['height'] \
                           / layer_config['height'] / 2.0)
                    )) + shift_y()
                    # for all neurons (in post layer) inside of the
                    # connect['radius'] with given central point
                    post_from_range_x = central_post_x - (radius - 1)
                    post_to_range_x = central_post_x + (radius - 1) + 1
                    if post_from_range_x < 0:
                        post_from_range_x = 0
                    if post_from_range_x >= post_layer_config['width']:
                        continue
                    if post_to_range_x < 0:
                        continue
                    if post_to_range_x > post_layer_config['width']:
                        post_to_range_x = post_layer_config['width']

                    post_from_range_y = central_post_y - (radius - 1)
                    post_to_range_y = central_post_y + (radius - 1) + 1
                    if post_from_range_y < 0:
                        post_from_range_y = 0
                    if post_from_range_y >= post_layer_config['height']:
                        continue
                    if post_to_range_y < 0:
                        continue
                    if post_to_range_y > post_layer_config['height']:
                        post_to_range_y = post_layer_config['height']
                    def post_layer_coords():
                        # for neurons in post layer
                        for post_y in xrange(
                            post_from_range_y,
                            post_to_range_y
                        ):
                            post_info_cache_y = post_info_cache[post_y]
                            for post_x in xrange(
                                post_from_range_x,
                                post_to_range_x
                            ):
                                inf = post_info_cache_y[post_x]
                                yield post_x, post_y, inf
                    for post_x, post_y, inf in post_layer_coords():
                        try:
                            # inf[0] - domain index
                            post_info_domain_name = domain_index_to_name[inf[0]]
                        except IndexError:
                            continue
                        # actually create connections
                        if post_info_domain_name == self.name:
                            # inf[1] - post layer index in domain
                            post_layer = self.layers[inf[1]]
                            self.synapse_address += 1
                            self_connect_neurons(
                                pre_neuron_address,
                                post_layer.neurons_metadata.level.to_address(
                                    post_x - post_layer.x,
                                    post_y - post_layer.y
                                ),
                                self.synapse_address
                            )
                        else:
                            # connect neurons with other domains
                            self.connect_remote_neurons(
                                pre_domain_index,
                                pre_layer_index,
                                pre_neuron_address,
                                int(inf[0]), # post domain index
                                int(inf[1]), # post layer index
                                post_x,
                                post_y
                            )
                        total_synapses[post_info_domain_name] += 1

    def create_neurons(self):
        """
        Создаем физически нейроны в ранее созданном векторе
        """
        logging.debug('Create neurons')
        for layer in self.layers:
            layer.create_neurons()

    def connect_neurons(self, pre_address, post_address, synapse_address):
        """
        Соединяем два нейрона с помощью синапса.
        """
        # Speedup this:
        #   synapses = self.synapses_metadata
        #   synapses.pre[synapse_address] = pre_address
        #   synapses.post[synapse_address] = post_address
        synapses_vector = self.synapses
        synapses_metadata = self.synapses_metadata
        if synapse_address >= synapses_metadata.pre.length:
            synapses_metadata.pre.resize()
            synapses_metadata.post.resize()
        synapses_vector.pre.data[synapse_address] = pre_address
        synapses_vector.post.data[synapse_address] = post_address

    def connect_remote_neurons(
        self,
        pre_domain_index, pre_layer_index, pre_neuron_address,
        post_domain_index, post_layer_index, post_x, post_y
    ):
        """
        Соединяем локальный нейрон с нейроном в другом домене
        self == pre_domain
        """
        # local pre neuron is transmitter
        self.neurons.flags[pre_neuron_address] |= IS_TRANSMITTER
        # get post_neuron_domain
        domain = self.net.domains[post_domain_index]
        # connect pre neuron with post neuron in post_neuron_domain
        domain.send_synapse(
            pre_domain_index, pre_layer_index, pre_neuron_address,
            post_layer_index, post_x, post_y)

    def send_synapse_pack(self, bytes=None):
        """
        Получаем сгруппированные данные и синапсах из удаленного домена
        """
        if not bytes:
            return
        packet = TransmitterVector()
        packet.from_bytes(bytes)
        for pos in range(packet.length):
            self.send_synapse(
                packet.pre_domain_index.data[pos],
                packet.pre_layer_index.data[pos],
                packet.pre_neuron_address.data[pos],
                packet.post_layer_index.data[pos],
                packet.post_x.data[pos],
                packet.post_y.data[pos]
            )
        # досылаем остатки
        for domain in self.net.domains:
            if isinstance(domain, RemoteDomainBase):
                domain.send_receiver_index_pack()

    def send_synapse(
        self,
        pre_domain_index, pre_layer_index, pre_neuron_address,
        post_layer_index, post_x, post_y):
        """
        Обрабатываем информацию о синапсе из другого домена
        self == post_domain
        """
        pre_domain = self.net.domains[pre_domain_index]
        pre_layer = pre_domain.layers[pre_layer_index]
        post_layer = self.layers[post_layer_index]
        local_pre_neuron_address \
                = self.receiver_index.get_local_address(
                    pre_domain_index, pre_neuron_address)
        # create IS_RECEIVER neuron
        if not local_pre_neuron_address:
            self.remote_neuron_address += 1
            # add pre_neuron to domain.remote_neurons_metadata if not added (use
            # create_neuron function)
            create_neuron(self.remote_neuron_address,
                          self.remote_neurons_metadata,
                          pre_layer,
                          pre_layer_index)
            # get local_pre_neuron_address
            local_pre_neuron_address = self.remote_neurons_metadata.level \
                    .to_address(self.remote_neuron_address, 0)
            if not self.receiver_index.add(
                local_pre_neuron_address,
                pre_domain_index,
                pre_neuron_address
            ):
                self.stat_inc('receiver_index_again')
            local_pre_neuron_receiver_index = self.receiver_index.pos
            # set IS_RECEIVER flag to pre_neuron
            self.remote_neurons_metadata.flags[self.remote_neuron_address] \
                    |= IS_RECEIVER
            # send local_pre_neuron_address back to source domain (pre_domain)
            pre_domain.send_receiver_index(self.index, pre_neuron_address,
                                           local_pre_neuron_address,
                                           local_pre_neuron_receiver_index)
            self.stat_inc('total_receiver_neurons')
            self.stat_set('send_synapse_time', datetime.datetime.utcnow())
        # get synapse_address
        self.synapse_address += 1
        self.connect_neurons(
            local_pre_neuron_address,
            post_layer.neurons_metadata.level.to_address(
                post_x - post_layer.x,
                post_y - post_layer.y
            ),
            self.synapse_address
        )

    def send_receiver_index_pack(self, bytes=None):
        """
        Получаем сгруппированные данные из удаленного домена
        """
        if not bytes:
            return
        packet = ReceiverVector()
        packet.from_bytes(bytes)
        for pos in xrange(packet.length):
            self.send_receiver_index(
                packet.post_domain_index.data[pos],
                packet.pre_neuron_address.data[pos],
                packet.remote_pre_neuron_address.data[pos],
                packet.remote_pre_neuron_receiver_index.data[pos]
            )

    def send_receiver_index(self, post_domain_index, pre_neuron_address,
                            remote_pre_neuron_address,
                            remote_pre_neuron_receiver_index):
        """
        Запоминаем remote_neuron_address (IS_RECEIVER) для pre_neuron_address
        (IS_TRANSMITTER)
        self == pre_domain
        """
        pre_domain = self
        if not pre_domain.transmitter_index.add(
            pre_neuron_address, post_domain_index, remote_pre_neuron_address,
            remote_pre_neuron_receiver_index
        ):
            pre_domain.stat_inc('transmitter_index_again')
        pre_domain.stat_inc('total_transmitter_neurons')
        pre_domain.stat_set('send_receiver_index_time',
                            datetime.datetime.utcnow())

    def send_spikes(self):
        """
        Получаем спайки из устройства (device) и отправляем их в другие домены.
        """
        # step 4
        self.device.tick_transmitter_index(self)
        # step 5
        self.transmitter_index.is_spiked.from_device(self.device)
        index = self.transmitter_index
        domains = self.net.domains
        remote_domain_data = index.remote_domain.data
        remote_receiver_index_data = index.remote_receiver_index.data
        register_spike = [domain.register_spike for domain in domains]
        for i, is_spiked in enumerate(index.is_spiked.data):
            if not is_spiked:
                continue
            receiver_neuron_index = remote_receiver_index_data[i]
            register_spike[remote_domain_data[i]](receiver_neuron_index)
        for post_domain in self.net.domains:
            if post_domain != self:
                # если post_domain локальный, то ничего не произойдет
                # если post_domain удаленный и у него накопились спайки,
                # то он опубликует эти спайки
                post_domain.register_spike_pack()

    def receive_spikes(self):
        """
        Получаем спайки из других доменов, формируем receiver index и копируем
        его в устройство (device).
        """
        # step 3
        # send to device info about new spikes
        self.receiver_index.is_spiked.to_device(self.device)
        self.device.tick_receiver_index(self)
        # get is_spiked filled with 0
        self.receiver_index.is_spiked.from_device(self.device)

    def register_spike_pack(self, bytes=None):
        """
        Обрабатываем спайки из удаленных доменов
        """
        if not bytes:
            return
        packet = SpikesVector()
        packet.from_bytes(bytes)
        self.stat_inc('spikes_received', packet.length)
        # speedup for commented version
        #for pos in range(packet.length):
        #    self.register_spike(
        #        packet.receiver_neuron_index.data[pos],
        #    )
        self.receiver_index.is_spiked.data[packet.receiver_neuron_index.data] \
                = 1


    def register_spike(self, receiver_neuron_index):
        """
        Записывает в домен пришедший спайк
        """
        # step 2
        self.receiver_index.is_spiked.data[receiver_neuron_index] = 1

    def register_input_layer_data(self, layer_index, data):
        """
        Регистрирует данные (в виде обычного или сериализованного numpy
        массива), пришедшие из других доменов.
        """
        self.layers[layer_index].register_input_data(data, self.ticks)


    def tick(self):
        """
        Один tick домена.
        0.
            - self.ticks++
            - self.total_spikes = 0 (эта информация накапливается в
                domain.stat_vector для поля 0)
        1. по всем слоям layer:
            - layer.total_spikes = 0 (эта информация накапливается в
                domain.layers_stat для поля 0)
            и по всем нейронам neuron в слое layer (device):
            - если neuron.flags & IS_DEAD - не обсчитываем нейрон
            - если флаг IS_SPIKED уже установлен - снимаем
            - если это IS_RECEIVER - заканчиваем обсчет нейрона
            - если neuron.level >= layer.threshold:
                - у neuron.flags устанавливаем флаг IS_SPIKED,
                - layer.total_spikes++
                - domain.total_spikes++
                - обнуляем neuron.level (либо уменьшаем neuron.level на
                  layer.threshold, что бы можно было сделать генераторы
                  импульсов. Тут надо подумать.)
                - neuron.tick = domain.tick
            в противном случае:
                - neuron.level -= layer.relaxation
            - если neuron.level < 0, то neuron.level = 0

        2. по всем сообщениям о спайках пришедшим из других доменов (cpu):
            - если сообщений не было - пропускаем шаг 3.
            - в противном случае формируем receiver index и копируем его в
              устройство (device)

        3. по всем записям в receiver index (device):
            - устанавливаем флаг IS_SPIKED у нейрона по адресу index.address[i]

        4. по всем записям в transmitter index (device):
            - если по адресу index.address у нейрона neuron.flags & IS_SPIKED,
              устанавливаем флаг IS_SPIKED у index.flags, в противном случае
              снимаем флаг

        5. получаем из устройства (device) transmitter index (cpu):
            - формируем сообщения для тех нейронов, у которых произошел спайк и
              асинхронно отправляем их в другие домены.

        6. по всем записям в pre_synapse_index.key (device):
            - если pre_synapse_index.key[i] == null - заканчиваем обсчет
            - если neuron.flags & IS_DEAD - обнуляем все синапсы
              (synapse.level = 0)
            - если не neuron.flags & IS_SPIKED, то заканчиваем обсчет
            - по всем записям в pre_synapse_index.value, относящимся к
              pre_synapse_index.key[i]:
                - если synapse.level == 0 - считаем что синапс мертв и не
                  обсчитываем дальше внутренний цикл
                - если post.flags & IS_DEAD - удаляем синапс (synapse.level = 0)
                  и не обсчитываем дальше внутренний цикл
                - если дошли до этого места, то neuron.flags & IS_SPIKED и
                  делаем:
                    - post.level += (neuron.flags & IS_INHIBITORY ?
                      -synapse.level : synapse.level)
                    # Обучение синапсов к post нейронам
                    - если neuron.tick - post.tick
                        < domain.spike_learn_threshold,
                      то увеличиваем вес синапса. Вес можно увеличивать,
                      например, как f(neuron.tick - post.tick), либо на
                      фиксированное значение
                    - если neuron.tick - post.tick
                        >= domain.spike_forget_threshold,
                      то уменьшаем вес синапса. Вес можно уменьшать, например,
                      как f(neuron.tick - post.tick), либо на фиксированное
                      значение
            - по всем записям в post_synapse_index.value, относящимся к
              post_synapse_index.key[i]:
                - если synapse.level == 0 - считаем что синапс мертв и не
                  обсчитываем дальше внутренний цикл
                - если pre.flags & IS_DEAD - удаляем синапс (synapse.level = 0)
                  и не обсчитываем дальше внутренний цикл
                # Обучение синапсов от pre нейронов
                - если neuron.tick - pre.tick <= domain.spike_learn_threshold,
                  то увеличиваем вес синапса. Вес можно увеличивать, например,
                  как f(neuron.tick - pre.tick), либо на фиксированное значение
                - если neuron.tick - pre.tick >= domain.spike_forget_threshold,
                  то уменьшаем вес синапса. Вес можно уменьшать, например, как
                  f(neuron.tick - pre.tick), либо на фиксированное значение

        """
        # step 0
        self.ticks += 1
        self.stat_set('ticks', self.ticks)
        # step 1
        self.device.tick_neurons(self)
        # step 2 & 3
        self.receive_spikes()
        # step 4 & 5
        self.send_spikes()
        # step 6
        self.device.tick_synapses(self)


