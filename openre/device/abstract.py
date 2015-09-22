# -*- coding: utf-8 -*-
"""
Интерфейс к различным устройствам, на которых будет моделироваться сеть.
"""

class Device(object):
    """
    Абстрактный класс для устройств
    """
    def __init__(self, config):
        self.config = config

    def tick_neurons(self, domain):
        """
        Проверяем нейроны на спайки.
        """
        raise NotImplementedError

    def tick_synapses(self, domain):
        """
        Передаем сигналы от pre-нейронов, у которых наступил спайк к
        post-нейронам
        """
        raise NotImplementedError

    def tick_transmitter_index(self, domain):
        """
        Получаем спайки из устройства для нейронов с флагом IS_TRANSMITTER
        """
        raise NotImplementedError

    def tick_receiver_index(self, domain):
        """
        Передаем в устройство спайки для нейронов с флагом IS_RECEIVER
        """
        raise NotImplementedError

    def create(self, data):
        """
        Создает указатель на данные на устройстве для data
        """
        raise NotImplementedError

    def upload(self, device_data_pointer, data, is_blocking=True):
        """
        Данные из data копируются на устройство и возвращается указатель
        на данные на устройсте
        """
        raise NotImplementedError

    def download(self, data, device_data_pointer, is_blocking=True):
        """
        Данные с устройства (указатель dev_data) копируются в data
        """
        raise NotImplementedError

