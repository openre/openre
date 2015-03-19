# -*- coding: utf-8 -*-
"""
Содержит в себе слои и синапсы.
"""
from openre.vector import Vector
from openre.metadata import Metadata
from openre.data_types import types
from openre.layer import Layer, LayersVector
from openre.neurons import NeuronsVector
from openre.sinapses import SinapsesVector, SinapsesMetadata
import logging
import uuid
import random
from copy import deepcopy
import math
from openre.index import Index
from openre import device
import numpy as np


class Domain(object):
    """
    Домен (Domain) - содержит один и более слоев состоящих из нейронов,
    связанных друг с другом синапсами. Домен можно воспринимать как один процесс
    в операционной системе, реализующий частично или полностью какой либо
    функционал. В некоторых случаях домен может не содержать синапсов (например,
    если домен является источником данных с сенсоров)

    self.id: types.address - должен быть уникальным для всех доменов
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
    self.learn_rate: types.sinapse_level - с какой скоростью увеличивается
                     sinapse.learn если у нейронов синапса расстояние между
                     спайками меньше чем self.spike_learn_threshold
    self.learn_threshold: types.sinapse_level - какой максимальный уровень может
                          быть у sinapse.learn. При спайке sinapse.learn
                          суммируется с sinapse.level (кратковременная память)
                          и суммарный сигнал передается post-нейрону.
                          Минимальный уровень у sinapse.learn == 0. При первом
                          достижении максимального уровня синапс должен
                          одноразово усиливаться (долговременная память).
    Жеательно что бы выполнялось условие:
        0 <= spike_learn_threshold <= spike_forget_threshold <= types.tick.max
    """
    def __init__(self, config, ore):
        logging.debug('Create domain (id: %s)', config['id'])
        config = deepcopy(config)
        self.config = config
        self.ore = ore
        self.id = self.config['id']
        self.ticks = 0
        self.spike_learn_threshold \
                = self.ore.config['sinapse'].get('spike_learn_threshold', 0)
        self.spike_forget_threshold \
                = self.ore.config['sinapse'].get('spike_forget_threshold', 0)
        self.learn_rate \
                = self.ore.config['sinapse'].get('learn_rate', 0)
        self.learn_threshold \
                = self.ore.config['sinapse'].get('learn_threshold', 0)
        self.layers = []
        self.layers_vector = LayersVector()
        # domain layers config
        self.layers_config = deepcopy(self.config['layers'])
        # neurons vector. Metadata stored in layer.neurons_metadata
        self.neurons = NeuronsVector()
        # sinapses vector
        self.sinapses = SinapsesVector()
        self.sinapses_metadata = None
        self.random = random.Random()
        self.seed = uuid.uuid4().hex
        self.pre_sinapse_index = None
        self.post_sinapse_index = None
        self.device = getattr(
            device,
            self.config['device'].get('type', 'OpenCL')
        )(self.config['device'])
        self.cache = {}
        # stats for domain (number of spikes)
        self.stat = Vector()
        # fields:
        # 0 - total spikes (one per neuron) per self.config['stat_size'] ticks
        # 1 - number of the dead neurons
        self.stat_fields = 2
        stat_metadata = Metadata(
            (1, self.stat_fields),
            types.stat
        )
        self.stat.add(stat_metadata)
        self.stat.create()
        # stats for vectors
        self.layers_stat = Vector()

        self.deploy()
        logging.debug('Domain created')

    def __repr__(self):
        return 'Domain(%s, %s)' % (repr(self.config), repr(self.ore))

    def deploy(self):
        """
        Создание слоев и нейронов, синапсов на основе self.config и
        загрузка данных на устройство (device - например, gpu или cpu)
        config.device
        """
        # Create layers
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
        for layer_config in self.layers_config:
            for connect in layer_config.get('connect', []):
                connect['domain_layers'] = []
            for layer in self.layers:
                for connect in layer_config.get('connect', []):
                    if connect['id'] == layer.id:
                        connect['domain_layers'].append(layer)
        logging.debug('Allocate layers vector')
        self.layers_vector.create()
        self.layers_stat.create()
        for layer_id, layer in enumerate(self.layers):
            self.layers_vector.threshold[layer_id] = layer.threshold
            self.layers_vector.relaxation[layer_id] = layer.relaxation
            self.layers_vector.spike_cost[layer_id] = layer.spike_cost
            self.layers_vector.max_vitality[layer_id] = layer.max_vitality

        # Count sinapses (first pass - virtual sinapses connections)
        total_sinapses = self.count_sinapses()
        # allocate sinapses buffer in memory
        domain_total_sinapses = total_sinapses.get(self.id, 0)
        if not domain_total_sinapses:
            logging.warn('No sinapses in domain %s', self.id)
        self.sinapses_metadata = SinapsesMetadata(domain_total_sinapses)
        self.sinapses.add(self.sinapses_metadata)
        logging.debug(
            'Allocate sinapses vector (%s sinapses in domain)',
            domain_total_sinapses
        )
        self.sinapses.create(0, self.ore.config['sinapse']['max_level'])
        # allocate neurons buffer in memory
        logging.debug(
            'Allocate neurons vector (%s neurons in domain)',
            len(self.neurons)
        )
        self.neurons.create()
        self.create_neurons()
        # Create sinapses (second pass)
        self.create_sinapses()
        # create pre-neuron - sinapse index
        logging.debug('Create pre-neuron - sinapse index')
        self.pre_sinapse_index = Index(len(self.neurons), self.sinapses.pre)
        # create post-neuron - sinapse index
        logging.debug('Create post-neuron - sinapse index')
        self.post_sinapse_index = Index(len(self.neurons), self.sinapses.post)
        # upload data on device
        logging.debug('Upload data to device')
        for vector in [
            self.layers_vector,
            self.neurons,
            self.sinapses,
            self.pre_sinapse_index,
            self.post_sinapse_index,
            self.layers_stat,
        ]:
            vector.create_device_data_pointer(self.device)

    def count_sinapses(self):
        """
        Подсчитываем количество синапсов, которое образуется в данном домене
        """
        logging.debug('Counting sinapses')
        # Domains sinapses
        total_sinapses = self.connect_layers(virtual=True)
        for domain_id in total_sinapses:
            if domain_id != self.id:
                # TODO: send sinapse counts (in total_sinapses) to other domains
                pass
        # TODO: recieve sinapse counts from other domains
        return total_sinapses

    def connect_layers(self, virtual=False):
        """
        Реализует непосредственное соединение слоев или (если virtual == True)
        подсчет синапсов без физического соединения
        """
        self.random.seed(self.seed)
        layer_config_by_id = {}
        total_sinapses = {}
        sinapse_address = -1
        # cache
        self_connect_neurons = self.connect_neurons
        for layer_config in self.ore.config['layers']:
            layer_config_by_id[layer_config['id']] = layer_config
        domain_index_to_id = []
        for domain_index, domain in enumerate(self.ore.config['domains']):
            domain_index_to_id.append(domain['id'])
            total_sinapses[domain['id']] = 0
        domain_index_to_id.append(None)
        # cache neurn -> domain and neuron -> layer in domain
        if 'layer' not in self.cache:
            self.cache['layer'] = {}
            for layer_config in self.ore.config['layers']:
                # heihgt x width x z,
                # where z == 0 is domain index in ore and
                #       z == 1 is layer index in domain
                self.cache['layer'][layer_config['id']] = \
                    np.zeros(
                        (layer_config['height'], layer_config['width'], 2),
                        dtype=np.int
                    )
                self.cache['layer'][layer_config['id']].fill(-1)
            for domain_index, domain in enumerate(self.ore.config['domains']):
                layer_index = -1
                for layer in domain['layers']:
                    layer_index += 1
                    layer = deepcopy(layer)
                    layer_config = layer_config_by_id[layer['id']]
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
                            self.cache['layer'][layer_config['id']]
                    for y in xrange(shape[1], shape[1] + shape[3]):
                        layer_cache_y = layer_cache[y]
                        for x in xrange(shape[0], shape[0] + shape[2]):
                            layer_cache_y[x][0] = domain_index
                            layer_cache_y[x][1] = layer_index

        # start connecting
        for layer_config in self.layers_config:
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

                post_layer_config = layer_config_by_id[connect['id']]
                post_info_cache = self.cache['layer'][post_layer_config['id']]
                radius = connect.get('radius', max(
                    int(1.0 * layer_config['width'] \
                        / post_layer_config['width'] / 2),
                    int(1.0 * layer_config['height'] \
                        / post_layer_config['height'] / 2)
                ) + 1)
                for pre_y in xrange(layer.y, layer.y + layer.height):
                    for pre_x in xrange(layer.x, layer.x + layer.width):
                        # Determine post x coordinate of neuron in post layer.
                        # Should be recalculated for every y because of possible
                        # random shift
                        layer_neuron_address = None
                        if not virtual:
                            layer_neuron_address = layer_to_address(
                                pre_x - layer.x,
                                pre_y - layer.y
                            )
                        central_post_x = int(math.floor(
                            1.0 * pre_x / (layer_config['width']) \
                            * (post_layer_config['width'])
                        )) + shift_x()
                        # determine post y coordinate of neuron in post layer
                        central_post_y = int(math.floor(
                            1.0 * pre_y / (layer_config['height']) \
                            * (post_layer_config['height'])
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
                            post_to_range_x = post_layer_config['width'] - 1

                        post_from_range_y = central_post_y - (radius - 1)
                        post_to_range_y = central_post_y + (radius - 1) + 1
                        if post_from_range_y < 0:
                            post_from_range_y = 0
                        if post_from_range_y >= post_layer_config['height']:
                            continue
                        if post_to_range_y < 0:
                            continue
                        if post_to_range_y > post_layer_config['height']:
                            post_to_range_y = post_layer_config['height'] - 1
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
                                post_info_domain_id = domain_index_to_id[inf[0]]
                                # actually create connections
                                if not virtual:
                                    if post_info_domain_id == self.id:
                                        # inf[1] - post layer index in domain
                                        post_layer = self.layers[inf[1]]
                                        sinapse_address += 1
                                        self_connect_neurons(
                                            layer_neuron_address,
                                            post_layer.neurons_metadata.level \
                                            .to_address(
                                                post_x - post_layer.x,
                                                post_y - post_layer.y
                                            ),
                                            sinapse_address
                                        )
                                    else:
                                        # TODO: connect neurons with other
                                        #       domains
                                        pass
                                else:
                                    total_sinapses[post_info_domain_id] += 1


        return total_sinapses

    def create_neurons(self):
        """
        Создаем физически нейроны в ранее созданном векторе
        """
        logging.debug('Create neurons')
        for layer in self.layers:
            layer.create_neurons()

    def create_sinapses(self):
        """
        Создаем физически синапсы в ранее созданном векторе
        """
        logging.debug('Create sinapses')
        self.connect_layers(virtual=False)

    def connect_neurons(self, pre_address, post_address, sinapse_address):
        """
        Соединяем два нейрона с помощью синапса.
        """
        sinapses = self.sinapses
        sinapses.pre.data[sinapse_address] = pre_address
        sinapses.post.data[sinapse_address] = post_address

    def send_spikes(self):
        """
        Получаем спайки из устройства (device) и отправляем их в другие домены.
        """

    def receive_spikes(self):
        """
        Получаем спайки из других доменов, формируем receiver index и копируем
        его в устройство (device).
        """

    def tick(self):
        """
        Один tick домена.
        0.
            - self.ticks++
            - self.total_spikes = 0 (эта информация накапливается в domain.stat
                для поля 0)
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

        6. по всем записям в pre_sinapse_index.key (device):
            - если pre_sinapse_index.key[i] == null - заканчиваем обсчет
            - если neuron.flags & IS_DEAD - обнуляем все синапсы
              (sinapse.level = 0)
            - если не neuron.flags & IS_SPIKED, то заканчиваем обсчет
            - по всем записям в pre_sinapse_index.value, относящимся к
              pre_sinapse_index.key[i]:
                - если sinapse.level == 0 - считаем что синапс мертв и не
                  обсчитываем дальше внутренний цикл
                - если post.flags & IS_DEAD - удаляем синапс (sinapse.level = 0)
                  и не обсчитываем дальше внутренний цикл
                - если дошли до этого места, то neuron.flags & IS_SPIKED и
                  делаем:
                    - post.level += (neuron.flags & IS_INHIBITORY ?
                      -sinapse.level : sinapse.level)
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
            - по всем записям в post_sinapse_index.value, относящимся к
              post_sinapse_index.key[i]:
                - если sinapse.level == 0 - считаем что синапс мертв и не
                  обсчитываем дальше внутренний цикл
                - если pre.flags & IS_DEAD - удаляем синапс (sinapse.level = 0)
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
        # step 1
        self.device.tick_neurons(self)
        # step 2 & 3
        self.receive_spikes()
        # step 4 & 5
        self.send_spikes()
        # step 6
        self.device.tick_sinapses(self)
