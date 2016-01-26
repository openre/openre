# -*- coding: utf-8 -*-
"""
Просим домен подписаться на события
"""

from openre.agent.decorators import action

@action(namespace='domain')
def subscribe(event, domain_id):
    """
    Просим этот домен подписаться на события из домена domain_id так
    как domain_id будет публиковать события для этого домена.
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
    if agent.context['subscribed_to'].get(domain_id):
        return True
    # find config by domain_id
    for domain_config in net.config['domains']:
        if domain_config['id'] == domain_id:
            config = domain_config
    if config:
        host = config.get('proxy', {}) \
                .get('host', config.get('server', {}).get('host', '127.0.0.1'))
        port = config.get('proxy', {}).get('port', 8932)
        origin = '%s:%s' % (host, port)
        # prevent to connect to the same origin twice
        if agent.context['subscribed_to'].get(origin):
            return True
        agent.sub.connect("tcp://%s:%s" % (host, port))
        agent.context['subscribed_to'][domain_id] = 1
        agent.context['subscribed_to'][origin] = 1
        return True
    return False
