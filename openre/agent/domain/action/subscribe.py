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
        agent.sub.connect("tcp://%s:%s" % (
            config.get('proxy', {}) \
                .get('host', config.get('server', {}).get('host', '127.0.0.1')),
            config.get('proxy', {}).get('port', 8932))
        )
        agent.context['subscribed_to'][domain_id] = 1
        return True
    return False
