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
            self.server_socket = agent.connect(config.get('host', '127.0.0.1'),
                                               config.get('port', 8934))
            self.transport = RPCBrokerProxy(
                self.server_socket,
                'broker_domain_proxy',
                config['id'],
                domain_index
            )

        # FIXME: optimize send_synapse (collect portion of data and send it in
        # one request)
        def __getattr__(self, name):
            def api_call(*args, **kwargs):
                if name != 'send_synapse':
                    print "%s(*%s, **%s)" % (name, args, kwargs)
                return
            return api_call
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
