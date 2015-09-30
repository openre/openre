# -*- coding: utf-8 -*-
import logging
from openre.agent.helpers import RPC, RPCBrokerProxy, Transport, RPCException
import uuid

class DomainError(Exception):
    pass

class Domain(Transport):
    """
    Содержит в себе настройки для конкретного домена
    """
    def __init__(self, config, index):
        super(Domain, self).__init__()
        self.config = config
        self.index = index
        self.state = {}
        self.is_domain_created = False
        domain_config = self.config['domains'][index]
        self.name = domain_config['name']
        self.id = uuid.uuid4()
        logging.debug('Create domain %s', self.name)
        self.connection = self.connect(
            domain_config.get('host', '127.0.0.1'),
            domain_config.get('port', 8932)
        )
        self.server = RPC(self.connection)
        self.broker = RPCBrokerProxy(self.connection, 'broker_proxy',
                                self.id)
        self.domain = RPCBrokerProxy(self.connection, 'broker_domain_proxy',
                                self.id, self.index)

    def refresh_state(self):
        """
        Обновляет информацию о состоянии удаленного домена
        """
        self.state = self.server.domain_state(id=self.id)

    def create(self):
        """
        Посылает команду серверу на создание пустого домена (без нейронов и
        синапсов)
        """
        assert not self.is_domain_created
        self.is_domain_created = True
        logging.debug('Create remote domain %s', self.name)
        if not self.server.domain_start(name=self.name, id=self.id, wait=False):
            raise DomainError('Domain "%s" creation failed' % self.name)

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
        if not self.is_domain_created:
            return
        try:
            self.server.domain_stop(id=self.id)
        except RPCException as error:
            logging.warning(str(error.result.get('error')))
        self.is_domain_created = False

    def clean(self):
        """
        Закрывает соединение.
        """
        logging.debug('Clean domain %s', self.name)
        self.clean_sockets()
