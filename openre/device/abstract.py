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

    def tick_sinapses(self, domain):
        """
        Передаем сигналы от pre-нейронов, у которых наступил спайк к
        post-нейронам
        """
        raise NotImplementedError

    def upload(self, data):
        """
        Данные из data копируются на устройство и возвращается указатель
        на данные на устройсте
        """
        raise NotImplementedError

    def download(self, data, device_data_pointer):
        """
        Данные с устройства (указатель dev_data) копируются в data
        """
        raise NotImplementedError

