# -*- coding: utf-8 -*-
"""
Базовый класс домена.
"""
from openre.helpers import StatsMixin
from copy import deepcopy

class DomainBase(StatsMixin):
    """
    Базовый класс домена. Все остальные домены (включая удаленные) должны
    наследоваться от него.
    """
    def __init__(self, config, net, domain_index):
        super(DomainBase, self).__init__()
        config = deepcopy(config)
        self.config = config
        self.net = net
        self.name = self.config['name']
        self.index = domain_index

    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, repr(self.name))

    def deploy_layers(self):
        """
        Create layers
        """
        raise NotImplementedError

    def deploy_neurons(self):
        """
        Create neurons
        """
        raise NotImplementedError

    def pre_deploy_synapses(self):
        """
        Init synapses vector
        """
        # allocate synapses buffer in memory
        raise NotImplementedError

    def deploy_synapses(self):
        """
        Create synapses
        """
        # Create synapses
        raise NotImplementedError

    def post_deploy_synapses(self):
        """
        Run after all domains is synced
        """
        raise NotImplementedError

    def deploy_indexes(self):
        """
        Create indexes
        """
        raise NotImplementedError

    def deploy_device(self):
        """
        Upload data to device
        """
        raise NotImplementedError

    def create_synapses(self):
        """
        Создаем физически синапсы
        """
        raise NotImplementedError

    def connect_layers(self):
        """
        Реализует непосредственное соединение слоев
        """
        raise NotImplementedError

    def create_neurons(self):
        """
        Создаем физически нейроны в ранее созданном векторе
        """
        raise NotImplementedError

    def connect_neurons(self, pre_address, post_address, synapse_address):
        """
        Соединяем два нейрона с помощью синапса.
        """
        raise NotImplementedError

    def connect_remote_neurons(
        self,
        pre_domain_index, pre_layer_index, pre_neuron_address,
        post_domain_index, post_layer_index, post_x, post_y
    ):
        raise NotImplementedError

    def send_synapse(
        self,
        pre_domain_index, pre_layer_index, pre_neuron_address,
        post_layer_index, post_x, post_y):
        """
        Обрабатываем информацию о синапсе из другого домена
        self == post_domain
        """
        raise NotImplementedError

    def send_receiver_index(self, post_domain_index, pre_neuron_address,
                            remote_pre_neuron_address,
                            remote_pre_neuron_receiver_index):
        """
        Запоминаем remote_neuron_address (IS_RECEIVER) для pre_neuron_address
        (IS_TRANSMITTER)
        self == pre_domain
        """
        raise NotImplementedError

    def send_spikes(self):
        """
        Получаем спайки из устройства (device) и отправляем их в другие домены.
        """
        raise NotImplementedError

    def receive_spikes(self):
        """
        Получаем спайки из других доменов, формируем receiver index и копируем
        его в устройство (device).
        """
        raise NotImplementedError

    def register_spike(self, receiver_neuron_index):
        """
        Записывает в домен пришедший спайк
        """
        raise NotImplementedError

    def tick(self):
        """
        Один tick домена.
        """
        raise NotImplementedError

