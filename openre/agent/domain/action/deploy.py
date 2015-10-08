# -*- coding: utf-8 -*-
"""
Загрузка конфига.
"""

from openre.agent.decorators import action
from openre.agent.domain.decorators import state
from openre.domain import create_domain_factory
from openre.domain.remote import RemoteDomainBase
from openre.agent.helpers import RPCBrokerProxy

def remote_domain_factory(agent):
    class RemoteDomain(RemoteDomainBase):
        """
        Прокси к удаленному домену.
        """
        def __init__(self, config, net, domain_index):
            super(RemoteDomain, self).__init__(config, net, domain_index)
            def lazy_socket():
                """Отложенное создание сокета"""
                self.server_socket = agent.connect(
                    config.get('host', '127.0.0.1'),
                    config.get('port', 8934))
                return self.server_socket
            self.server_socket = lazy_socket
            self.transport = RPCBrokerProxy(
                self.server_socket,
                'broker_domain_proxy',
                config['id'],
                domain_index
            )

        def send_synapse(self,
            pre_domain_index, pre_layer_index, pre_neuron_address,
            post_layer_index, post_x, post_y):
            """
            Обрабатываем информацию о синапсе из другого домена
            self == post_domain
            """
            # FIXME: optimize send_synapse (collect portion of data and send
            # it in one request)
            return self.__getattr__('send_synapse').no_reply(
                pre_domain_index, pre_layer_index, pre_neuron_address,
                post_layer_index, post_x, post_y)

        def send_receiver_index(self, post_domain_index, pre_neuron_address,
                                remote_pre_neuron_address,
                                remote_pre_neuron_receiver_index):
            """
            Запоминаем remote_neuron_address (IS_RECEIVER) для
            pre_neuron_address (IS_TRANSMITTER)
            self == pre_domain
            """
            return self.__getattr__('send_receiver_index').no_reply(
                post_domain_index, pre_neuron_address,
                remote_pre_neuron_address,
                remote_pre_neuron_receiver_index)

        def __getattr__(self, name):
            return getattr(self.transport, name)
    return RemoteDomain

@action(namespace='domain')
@state('deploy_domains')
def deploy_domains(event, local_domains=None):
    """
    Указываем какие домены будут локальными и создаем их.
    local_domains - список имен доменов в конфиге, которые будут моделироваться
        локально
    """
    agent = event.pool.context['agent']
    net = agent.context['net']
    remote_domain_class = remote_domain_factory(agent)
    net.deploy_domains(create_domain_factory(
        remote_domain_class=remote_domain_class,
        local_domains=local_domains
    ))

@action(namespace='domain')
@state('deploy_layers')
def deploy_layers(event):
    """
    Создание слоев.
    """
    agent = event.pool.context['agent']
    net = agent.context['net']
    net.deploy_layers()

@action(namespace='domain')
@state('deploy_neurons')
def deploy_neurons(event):
    """
    Создание пустых векторов нейронов.
    """
    agent = event.pool.context['agent']
    net = agent.context['net']
    net.deploy_neurons()

@action(namespace='domain')
@state('pre_deploy_synapses')
def pre_deploy_synapses(event):
    """
    Создание пустого вектора нейронов.
    """
    agent = event.pool.context['agent']
    net = agent.context['net']
    net.pre_deploy_synapses()

@action(namespace='domain')
@state('deploy_synapses')
def deploy_synapses(event):
    """
    Создание нейронов и синапсов.
    """
    agent = event.pool.context['agent']
    net = agent.context['net']
    net.deploy_synapses()

@action(namespace='domain')
@state('post_deploy_synapses')
def post_deploy_synapses(event):
    """
    Удаление пустого места с конца вектора синапсов.
    """
    agent = event.pool.context['agent']
    net = agent.context['net']
    net.post_deploy_synapses()

@action(namespace='domain')
@state('post_deploy')
def post_deploy(event):
    """
    Создание дополнительных индексов и загрузка данных на устройство.
    """
    agent = event.pool.context['agent']
    net = agent.context['net']
    net.post_deploy()


