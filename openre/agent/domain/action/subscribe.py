# -*- coding: utf-8 -*-
"""
Просим домен подписаться на события
"""

from openre.agent.decorators import action

@action(namespace='domain')
def subscribe(event, domain_index):
    """
    Просим этот домен подписаться на события из домена domain_index так
    как domain_index будет публиковать события для этого домена.
    Подписываемся только один раз на host:port, что бы не получать одно и то же
    сообщение дважды.
    """
    agent = event.pool.context['agent']
    if 'net' not in agent.context:
        return False
    net = agent.context['net']
    if 'subscribed_to' not in agent.context:
        agent.context['subscribed_to'] = {}
    config = None
    if agent.context['subscribed_to'].get(domain_index):
        return True
    # find config by domain_index
    config = net.config['domains'][domain_index]
    if config:
        host = config.get('proxy', {}) \
                .get('host', config.get('server', {}).get('host', '127.0.0.1'))
        port = config.get('proxy', {}).get('port', 8934)
        origin = '%s:%s' % (host, port)
        net.domains[domain_index].broker.subscribe_register.inc_priority \
                .no_reply(agent.context['local_domain'].index)
        # prevent to connect to the same origin twice
        if agent.context['subscribed_to'].get(origin):
            return True
        agent.sub.connect("tcp://%s:%s" % (host, port))
        agent.context['subscribed_to'][domain_index] = 1
        agent.context['subscribed_to'][origin] = 1
        return True
    return False

@action(namespace='domain')
def subscribe_register(event, domain_index):
    """
    Сюда приходит сообщение о том что domain_index удачно подписался на события
    из этого домена
    """
    agent = event.pool.context['agent']
    net = agent.context['net']
    net.domains[domain_index].is_subscribed = True
