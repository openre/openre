# -*- coding: utf-8 -*-
"""
Содержит в себе слои и синапсы.
"""
from openre.layer import Layer
from openre.neurons import NeuronsVector
import logging

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
    def __init__(self, config):
        logging.debug('Create domain (id: %s)', config['id'])
        self.config = config
        self.id = self.config['id']
        self.ticks = 0
        self.learn_threshold = self.config.get('learn_threshold', 0)
        self.forget_threshold = self.config.get('forget_threshold', 0)
        self.total_spikes = 0
        self.layers = []
        self.neurons = NeuronsVector()
        self.deploy()
        logging.debug('Domain created')

    def deploy(self):
        """
        Создание слоев и нейронов, синапсов на основе self.config и
        загрузка данных на устройство (device - например, gpu или cpu)
        config.device
        """
        layer_id = -1
        for layer_config in self.config['layers']:
            layer_id += 1
            layer_config['id'] = layer_id
            layer = Layer(layer_config)
            self.neurons.add(layer.metadata)
            layer.address = layer.metadata.address
            self.layers.append(layer)

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
