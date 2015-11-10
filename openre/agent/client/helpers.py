# -*- coding: utf-8 -*-
import logging
from openre.agent.helpers import RPC, RPCBrokerProxy, Transport, RPCException, \
        pretty_func_str
import uuid


def prepare_config(config):
    """
    Добавляет уникальный id для доменов. Необходим при создании новых
    agent.domain.
    Проверяет имя домена на наличие и на уникальность.
    """
    was_name = {}
    for domain_index, domain_config in enumerate(config['domains']):
        if 'name' not in domain_config:
            raise ValueError(
                'No name for domain with index %s in config["domains"]' %
                domain_index)
        name = domain_config['name']
        if name in was_name:
            raise ValueError(
                'Domain name "%s" already was in domain with index %s' %
                (name, was_name[name])
            )

        was_name[name] = domain_index
        if 'id' not in domain_config:
            domain_config['id'] = uuid.uuid4()


class DomainError(Exception):
    pass

class SimpleRCPCall(object):
    def __init__(self, proxy, name, domain_name):
        self.proxy = proxy
        self.name = name
        self.domain_name = domain_name
        self._priority = 0

    def set_priority(self, priority=0):
        """
        Устанавливает приоритет команды
        """
        self._priority = priority
        return self

    def __call__(self, *args, **kwargs):
        logging.debug(
            pretty_func_str(
                '%s.%s' % (self.domain_name, self.name), *args, **kwargs
            )
        )
        return getattr(self.proxy, self.name)(*args, **kwargs)


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
        logging.debug('%s.deploy_domains()', self.name)
        self.broker.deploy_domains([self.name])

    def __getattr__(self, name):
        return SimpleRCPCall(self.broker, name, self.name)

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

def test_config_helpres():
    from pytest import raises
    with raises(ValueError):
        prepare_config({
            "domains": [
                {
                    "layers"    : [
                        {"name": "V1"},
                        {"name": "V2"}
                    ]
                },
            ]
        })
    with raises(ValueError):
        prepare_config({
            "domains": [
                {
                    "name"        : "D2",
                    "layers"    : [
                        {"name": "V1"},
                    ]
                },
                {
                    "name"        : "D2",
                    "layers"    : [
                        {"name": "V3"}
                    ]
                }
            ]
        })
    config = {
        "domains": [
            {
                "name"        : "D1",
                "layers"    : [
                    {"name": "V1"},
                ]
            },
            {
                "name"        : "D2",
                "layers"    : [
                    {"name": "V3"}
                ]
            }
        ]
    }
    prepare_config(config)
    assert config['domains'][0]['id']
    assert config['domains'][1]['id']

