# -*- coding: utf-8 -*-
import logging
from openre.agent.helpers import RPC, RPCProxy, Transport
import uuid

class Domain(Transport):
    """
    Содержит в себе настройки для конкретного домена
    """
    def __init__(self, config, index):
        super(Domain, self).__init__()
        self.config = config
        self.index = index
        domain_config = self.config['domains'][index]
        self.id = domain_config['id']
        self.proccess_id = uuid.uuid4()
        logging.debug('Create domain %s', self.id)
        self.connection = self.connect(
            domain_config.get('host', '127.0.0.1'),
            domain_config.get('port', 8932)
        )
        self.server = RPC(self.connection)
        self.domain = RPCProxy(self.connection, 'domain_proxy')

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
        self.clean_sockets()
