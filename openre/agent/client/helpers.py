# -*- coding: utf-8 -*-
import logging

class ConnectionManager(object):
    """
    Подключается к серверу. Позволяет посылать запросы и получать ответы.
    """
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.connection = None

    def clean(self):
        """
        Закрывает соединение.
        """
        if self.connection:
            logging.debug('Close remote connection.')
            self.connection.close()
            self.connection = None

class ConnectionPool(object):
    """
    Содержит в себе объекты класса ConnectionManager. Занимается опросом всех
    соединений из объектов ConnectionManager.
    """

class Domain(object):
    """
    Содержит в себе настройки для конкретного домена
    """
    def __init__(self, config, index):
        self.config = config
        self.index = index
        domain_config = self.config['domains'][index]
        self.id = domain_config['id']
        logging.debug('Create domain %s', self.id)
        self.server = ConnectionManager(
            domain_config.get('host', '127.0.0.1'),
            domain_config.get('port', 8932)
        )

    def create(self):
        """
        Посылает команду сервреу на создание пустого домена (без нейронов и
        синапсов)
        """
        logging.debug('Create remote domain %s', self.id)

    def start(self):
        """
        Запускает симуляцию на домене
        """

    def pause(self):
        """
        Ставит на паузу симуляцию (без завершения основного цикла)
        """

    def stop(self):
        """
        Останавливает симуляцию, получает все данные с устройства, завершает
        основной цикл.
        """

    def destroy(self):
        """
        Посылает серверу команду на завершение работы домена.
        """

    def clean(self):
        """
        Закрывает соединение.
        """
        logging.debug('Clean domain %s', self.id)
        self.server.clean()
