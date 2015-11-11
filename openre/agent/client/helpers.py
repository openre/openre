# -*- coding: utf-8 -*-
import logging
from openre.agent.helpers import RPC, RPCBrokerProxy, Transport, RPCException, \
        pretty_func_str
import uuid
from openre.agent.client.decorators import proxy_call_to_domains
from openre.agent.decorators import wait
import datetime


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
        try:
            self.server.domain_stop(id=self.id)
        except RPCException as error:
            logging.warning(str(error.result.get('error')))

    def clean(self):
        """
        Закрывает соединение.
        """
        logging.debug('Clean domain %s', self.name)
        self.clean_sockets()

class Net(object):
    """
    Класс, управляющий доменами
    self.task - какое задание выполняется в данный момент
        new - сеть только создана и заполнена пустыми доменами
        create - послан запрос на создание доменов-агентов
        upload_config - загружается конфиг и создаются локальные домены
    self.state - в каком состоянии текущее задание
        run - выполняется
        pause - на паузе
        error - выполнено неудачно
        success - выполнено удачно

    """
    def __init__(self, config):
        self.config = config
        self.domains = []
        self.task = None
        self.state = None
        self.set_task('new', state='run')
        prepare_config(self.config)
        for domain_index, domain_config in enumerate(self.config['domains']):
            domain = Domain(config, domain_index)
            self.domains.append(domain)
        self.set_task(state='success')

    @wait(timeout=0, period=2)
    def ensure_domain_time_infinite(self, *args, **kwargs):

        """
        Ждем пока время последней отправки синапса к удаленному нейрону
            domain.stat('send_synapse_time') и
            время отправки информации об удаленном нейроне обратно
            domain.stat(''send_receiver_index_time') было больше или равно двум
            секундам.
        """
        # FIXME: async call to domains
        now = datetime.datetime.utcnow()
        for domain in self.domains:
            stats = domain.domain.stat.set_priority(2000000).wait() or {}
            for stat_field in ['send_synapse_time', 'send_receiver_index_time']:
                if stats.get(stat_field) \
                   and stats.get(stat_field) \
                   > now - datetime.timedelta(seconds=2):
                    return False
        return True

    @wait(timeout=0, period=2)
    def ensure_domain_idle_infinite(self, *args, **kwargs):

        """
        Ждем пока у домена не закончатся таски. Опрашиваемшиваем все домены раз
        в 2 секунды.
        """
        # FIXME: async call to domains
        for domain in self.domains:
            number_of_events = domain.broker.events \
                    .set_priority(2000000).wait()
            if number_of_events > 1: # have unfinished tasks
                return False
        return True

    @wait(timeout=10, period=0.5)
    def ensure_domain_state(self, *args, **kwargs):
        """
        Ждем правильного статуса в течение 10 секунд
        """
        return self._ensure_domain_state(*args, **kwargs)

    @wait(timeout=0, period=2)
    def ensure_domain_state_infinite(self, *args, **kwargs):
        """
        Бесконечно ждем правильного статуса. Опрашиваем домены раз в 2 секунды.
        """
        return self._ensure_domain_state(*args, **kwargs)

    def _ensure_domain_state(self, expected_state, expected_status='done'):
        """
        Ждем подтверждения от сервера, что у всех доменов появилось нужное
        состояние и статус.
        """
        # FIXME: async call to domains
        if not isinstance(expected_state, list):
            expected_state = [expected_state]
        if not isinstance(expected_status, list):
            expected_status = [expected_status]
        total_ok = 0
        for domain in self.domains:
            if not domain.state \
               or domain.state.get('state') not in expected_state \
               or domain.state.get('status') not in expected_status:
                domain.refresh_state()
            if domain.state and domain.state.get('status') == 'error':
                raise DomainError(domain.state.get('message'))
            if domain.state and domain.state.get('state') in expected_state \
               and domain.state.get('status') in expected_status:
                total_ok += 1
        if total_ok == len(self.domains):
            return True
        return False

    def set_task(self, task=None, state=None):
        """
        Устанавливает текущую задачу и состояние в котором она находится
        """
        if not task is None:
            self.task = task
            logging.debug('Set net task to "%s"', self.task)
        if not state is None:
            self.state = state
            logging.debug('Set net task "%s" to state "%s"',
                          self.task, self.state)
        return (self.task, self.state)

    @proxy_call_to_domains()
    def create(self):
        """
        Посылает команду на создание удаленных доменов
        """
        self.ensure_domain_state('blank')

    @proxy_call_to_domains()
    def upload_config(self):
        """
        Загружает конфиг на удаленные домены
        """
        self.ensure_domain_state('config')

    @proxy_call_to_domains()
    def deploy_domains(self):
        """
        Создает пустые домены. Можно не ждать окончания задачи.
        """
        self.ensure_domain_state('deploy_domains')

    @proxy_call_to_domains()
    def deploy_layers(self):
        """
        Создает слои. Можно не ждать окончания задачи.
        """
        self.ensure_domain_state('deploy_layers')

    @proxy_call_to_domains()
    def deploy_neurons(self):
        """
        Создает нейроны. Можно не ждать окончания задачи.
        """
        self.ensure_domain_state_infinite('deploy_neurons')

    @proxy_call_to_domains()
    def pre_deploy_synapses(self):
        """
        Готовимся к созданию нейронов. Синхронизируем все домены после этой
        задачи.
        """
        self.ensure_domain_state('pre_deploy_synapses')

    @proxy_call_to_domains()
    def deploy_synapses(self):
        """
        Создаем нейроны и синапсы. Это долгая задача. Синхронизируем все домены
        после этой задачи, так как после окончания создания синапсов в одном
        домене ему могут поступать синапсы из других доменов.
        """
        self.ensure_domain_state_infinite('deploy_synapses')
        self.ensure_domain_time_infinite()
        self.ensure_domain_idle_infinite()

    @proxy_call_to_domains()
    def post_deploy_synapses(self):
        """
        Удаляем неиспользованную часть вектора синапсов.
        """
        self.ensure_domain_state_infinite('post_deploy_synapses')

    @proxy_call_to_domains()
    def post_deploy(self):
        """
        Создаем индексы и загружаем их в устройство. Эта задача может быть
        долгой.
        """
        self.ensure_domain_state_infinite('post_deploy')

    def destroy(self):
        """
        Удаляет (destroy) удаленные (remote) домены, если они не были запущены.
        """
        for domain in self.domains:
            domain.destroy()

    def clean(self):
        """
        Если удаленные домены уже созданы - завершаем их работу.
        Закрываем все соединения доменов.
        """
        for domain in self.domains:
            domain.clean()

    @proxy_call_to_domains(priority=-1)
    def run(self):
        """
        Запускает симуляцию на домене
        """

    @proxy_call_to_domains()
    def start(self):
        """
        Запускает симуляцию, поставленную на паузу
        """

    @proxy_call_to_domains()
    def pause(self):
        """
        Ставит на паузу симуляцию (без завершения основного цикла)
        """

    @proxy_call_to_domains()
    def stop(self):
        """
        Останавливает симуляцию, получает все данные с устройства, завершает
        основной цикл.
        """

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


