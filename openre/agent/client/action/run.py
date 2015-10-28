# -*- coding: utf-8 -*-

from openre.agent.decorators import action
from openre.agent.client.helpers import Domain, DomainError
from openre.agent.client.decorators import proxy_call_to_domains
import logging
from openre.agent.decorators import wait
import uuid

@action(namespace='client')
def run(agent):
    logging.debug('Run Net')
    config = agent.net_config
    if not config:
        raise ValueError('No net config')
    net = None
    try:
        logging.info('Creating Net')
        net = Net(config)
        net.create()
        net.upload_config()
        net.deploy_domains()
        net.deploy_layers()
        net.deploy_neurons()
        net.pre_deploy_synapses()
        logging.info('Start creating neurons and synapses.' \
                     ' This may take a while.')
        net.deploy_synapses()
        logging.info('Upload data to devices')
        net.post_deploy_synapses()
        net.post_deploy()
        logging.info('Deploy done')
        # debug code:
        import time
        for _ in range(10):
            for domain in net.domains:
                stats = domain.domain.stat.wait() or {}
                print '%s:' % domain.name
                for key in sorted(stats.keys()):
                    print '    %s %s' % (key, stats[key])
            time.sleep(5)

    finally:
        if net:
            logging.info('Destroying Net')
            net.destroy()
            net.clean()

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
        for domain_index, domain_config in enumerate(self.config['domains']):
            if 'name' not in domain_config:
                self.set_task(state='error')
                raise ValueError(
                    'No name for domain with index %s in config["domains"]',
                    domain_index)
            if 'id' not in domain_config:
                domain_config['id'] = uuid.uuid4()
            domain = Domain(config, domain_index)
            self.domains.append(domain)
        self.set_task(state='success')

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

    @proxy_call_to_domains
    def create(self):
        """
        Посылает команду на создание удаленных доменов
        """
        self.ensure_domain_state('blank')

    @proxy_call_to_domains
    def upload_config(self):
        """
        Загружает конфиг на удаленные домены
        """
        self.ensure_domain_state('config')

    @proxy_call_to_domains
    def deploy_domains(self):
        """
        Создает пустые домены. Можно не ждать окончания задачи.
        """
        self.ensure_domain_state('deploy_domains')

    @proxy_call_to_domains
    def deploy_layers(self):
        """
        Создает слои. Можно не ждать окончания задачи.
        """
        self.ensure_domain_state('deploy_layers')

    @proxy_call_to_domains
    def deploy_neurons(self):
        """
        Создает нейроны. Можно не ждать окончания задачи.
        """
        self.ensure_domain_state('deploy_neurons')

    @proxy_call_to_domains
    def pre_deploy_synapses(self):
        """
        Готовимся к созданию нейронов. Синхронизируем все домены после этой
        задачи.
        """
        self.ensure_domain_state('pre_deploy_synapses')

    @proxy_call_to_domains
    def deploy_synapses(self):
        """
        Создаем нейроны и синапсы. Это долгая задача. Синхронизируем все домены
        после этой задачи, так как после окончания создания синапсов в одном
        домене ему могут поступать синапсы из других доменов.
        """
        self.ensure_domain_state_infinite('deploy_synapses')

    @proxy_call_to_domains
    def post_deploy_synapses(self):
        """
        Удаляем неиспользованную часть вектора синапсов.
        """
        self.ensure_domain_state('post_deploy_synapses')

    @proxy_call_to_domains
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

    def stop(self):
        """
        Останавливает удаленные домены, если они уе были запущены.
        """
        for domain in self.domains:
            domain.stop()

    def clean(self):
        """
        Если удаленные домены уже созданы - завершаем их работу.
        Закрываем все соединения доменов.
        """
        for domain in self.domains:
            domain.clean()
