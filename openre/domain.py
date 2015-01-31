# -*- coding: utf-8 -*-
"""
Содержит в себе слои и синапсы.
"""
from openre.layer import Layer
from openre.neurons import NeuronsVector
from openre.sinapses import SinapsesVector, SinapsesMetadata
import logging
import uuid
import random
from copy import deepcopy
import math
from openre.errors import OreNoSinapsesError


class Domain(object):
    """
    Домен (Domain) - содержит один и более слоев состоящих из нейронов,
    связанных друг с другом синапсами. Домен можно воспринимать как один процесс
    в операционной системе, реализующий частично или полностью какой либо
    функционал.

    self.id: types.address - должен быть уникальным для всех доменов
    self.ticks: types.tick - номер тика с момента запуска. При 32 битах и 1000
                             тиков в секунду переполнение произойдет через 49
                             дней. При 64 битах через 584 млн. лет.
    self.learn_threshold: types.tick - как близко друг к другу по времени
                                       должен сработать pre и post нейрон,
                                       что бы поменялся вес синапса в большую
                                       сторону.
                                       0 - по умолчанию (сеть не обучается).
    self.forget_threshold: types.tick - насколько сильной должна быть разница
                                        между pre.tick и post.tick что бы
                                        уменьшился вес синапса.
                                        0 - по умолчанию (сеть не забывает).
    self.total_spikes: types.address - количество спайков в домене за последний
                                       тик
    self.layers - список слоев (class Layer) домена
    Жеательно что бы выполнялось условие:
        0 <= learn_threshold <= forget_threshold <= types.tick.max
    """
    def __init__(self, config, ore):
        logging.debug('Create domain (id: %s)', config['id'])
        config = deepcopy(config)
        self.config = config
        self.ore = ore
        self.id = self.config['id']
        self.ticks = 0
        self.learn_threshold = self.config.get('learn_threshold', 0)
        self.forget_threshold = self.config.get('forget_threshold', 0)
        self.total_spikes = 0
        self.layers = []
        self.layers_config = deepcopy(self.config['layers'])
        self.neurons = NeuronsVector()
        self.sinapses = SinapsesVector()
        self.sinapses_metadata = None
        self.random = random.Random()
        self.seed = uuid.uuid4().hex
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
            self.neurons.add(layer.metadata)
            layer.address = layer.metadata.address
            self.layers.append(layer)
            layer_config['layer'] = layer
        for layer_config in self.layers_config:
            for connect in layer_config.get('connect', []):
                connect['domain_layers'] = []
            for layer in self.layers:
                for connect in layer_config.get('connect', []):
                    if connect['id'] == layer.id:
                        connect['domain_layers'].append(layer)
        # Count sinapses (first pass - virtual sinapses connections)
        total_sinapses = self.count_sinapses()
        # allocate sinapses buffer in memory
        domain_total_sinapses = total_sinapses.get(self.id, 0)
        if not domain_total_sinapses:
            raise OreNoSinapsesError('No sinapses in domain %s', self.id)

        self.sinapses_metadata = SinapsesMetadata(domain_total_sinapses)
        self.sinapses.add(self.sinapses_metadata)
        self.sinapses.create()
        # Create sinapses (second pass)
        self.create_sinapses()

    def count_sinapses(self):
        """
        Подсчитываем количество синапсов, которое образуется в данном домене
        """
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
        for layer_config in self.ore.config['layers']:
            layer_config_by_id[layer_config['id']] = layer_config
        for layer_config in self.layers_config:
            # no connections with other layers
            if not layer_config.get('connect'):
                continue
            # pre layer. Connect only neurons in this domain
            layer = layer_config['layer']
            for connect in layer_config.get('connect', []):
                radius = connect.get('radius', 1)
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
                for pre_x in xrange(layer.x, layer.x + layer.width):
                    for pre_y in xrange(layer.y, layer.y + layer.height):
                        # Determine post x coordinate of neuron in post layer.
                        # Should be recalculated for every y because of possible
                        # random shift
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
                        for post_x in xrange(
                            central_post_x - (radius - 1),
                            central_post_x + (radius - 1) + 1
                        ):
                            if post_x < 0:
                                continue
                            if post_x >= post_layer_config['width']:
                                continue
                            for post_y in xrange(
                                central_post_y - (radius - 1),
                                central_post_y + (radius - 1) + 1
                            ):
                                if post_y < 0:
                                    continue
                                if post_y >= post_layer_config['height']:
                                    continue
                                # TODO:
                                #  - get domain and layer by
                                #    post_layer_config['id'] and post_x, post_y
                                #  - if this is current domain - connect pre
                                #    and post neurons
                                post_info = self.ore.find(
                                    post_layer_config['id'], post_x, post_y)
                                # not found
                                if not post_info:
                                    continue
                                if post_info['domain_id'] not in total_sinapses:
                                    total_sinapses[post_info['domain_id']] = 0
                                total_sinapses[post_info['domain_id']] += 1
                                if post_info['domain_id'] == self.id:
                                    if not virtual:
                                        # TODO: connect two neurons with sinapse
                                        pass
                                else:
                                    # TODO: connect with other domain
                                    pass

#                                print '%s:%s -> %s:%s[%s]' % (
#                                    self.id,
#                                    layer.id,
#                                    post_info['domain_id'],
#                                    post_layer_config['id'],
#                                    post_info['layer_index']
#                                )

        return total_sinapses

    def create_sinapses(self):
        """
        Создаем физически синапсы в ранее созданном векторе
        """
        self.random.seed(self.seed)

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
            - self.total_spikes = 0
        1. по всем слоям layer:
            - layer.total_spikes = 0
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
                - если sinapse.level == 0 - считаем что синапс мертв, удаляем
                  его из индекса pre_sinapse_index и не обсчитываем дальше
                - если post.flags & IS_DEAD - удаляем синапс (sinapse.level = 0)
                  и удаляем его из индекса pre_sinapse_index и не обсчитываем
                  дальше
                - если дошли до этого места, то neuron.flags & IS_SPIKED и
                  делаем:
                    - post.level += (neuron.flags & IS_INHIBITORY ?
                      -sinapse.level : sinapse.level)
                    # Обучение синапсов к post нейронам
                    - если neuron.tick - post.tick <= domain.learn_threshold,
                      то увеличиваем вес синапса. Вес можно увеличивать,
                      например, как f(neuron.tick - post.tick), либо на
                      фиксированное значение
                    - если neuron.tick - post.tick >= domain.forget_threshold,
                      то уменьшаем вес синапса. Вес можно уменьшать, например,
                      как f(neuron.tick - post.tick), либо на фиксированное
                      значение
            - по всем записям в post_sinapse_index.value, относящимся к
              post_sinapse_index.key[i]:
                # Обучение синапсов от pre нейронов
                - если neuron.tick - pre.tick <= domain.learn_threshold, то
                  увеличиваем вес синапса. Вес можно увеличивать, например, как
                  f(neuron.tick - pre.tick), либо на фиксированное значение
                - если neuron.tick - pre.tick >= domain.forget_threshold, то
                  уменьшаем вес синапса. Вес можно уменьшать, например, как
                  f(neuron.tick - pre.tick), либо на фиксированное значение

        """
        # step 0
        self.ticks += 1
        self.total_spikes = 0
        # step 1
        # step 2 & 3
        self.receive_spikes()
        # step 4 & 5
        self.send_spikes()
        # step 6
