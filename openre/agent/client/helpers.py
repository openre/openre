# -*- coding: utf-8 -*-
import logging
from openre.agent.helpers import RPC, RPCBrokerProxy, Transport, RPCException

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
        self.id = domain_config['id']
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

    def upload_config(self):
        """
        Загружает конфиг
        """
        logging.debug('Upload config to remote domain %s', self.name)
        self.broker.config(self.config)

    def deploy_domains(self):
        """
        Создает удаленные домены указывая какие из них будут локальными, а какие
        глобальными
        """
        logging.debug('Deploy domains on %s', self.name)
        self.broker.deploy_domains([self.name])

    def deploy_layers(self):
        """
        Создает слои на удаленном домене.
        """
        logging.debug('Deploy layers on %s', self.name)
        self.broker.deploy_layers()

    def deploy_neurons(self):
        """
        Создает нейроны на удаленном домене.
        """
        logging.debug('Deploy neurons on %s', self.name)
        self.broker.deploy_neurons()

    def pre_deploy_synapses(self):
        """
        Инициализируется вектор синапсов.
        """
        logging.debug('Pre-deploy synapses on %s', self.name)
        self.broker.pre_deploy_synapses()

    def deploy_synapses(self):
        """
        Создание синапсов и нейронов в домене.
        """
        logging.debug('Deploy synapses on %s', self.name)
        self.broker.deploy_synapses()

    def post_deploy_synapses(self):
        """
        Удаляется неиспользуемое место в векторе синапсов.
        """
        logging.debug('Post-deploy synapses on %s', self.name)
        self.broker.post_deploy_synapses()

    def post_deploy(self):
        """
        Создаются индексы и данные загружаются на устройство.
        """
        logging.debug('Post-deploy on %s', self.name)
        self.broker.post_deploy()

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
