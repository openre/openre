# -*- coding: utf-8 -*-

from openre.agent.decorators import action, wait
import uuid
from openre.agent.helpers import RPCBrokerProxy, RPCException
import time

@wait(timeout=10, period=0.5)
def ensure_domain_state(agent, domain_id, expected_state,
                        expected_status='done'):
    """
    Ждем подтверждения от сервера, что у всех доменов появилось нужное
    состояние и статус.
    """
    state = agent.server.domain_state(id=domain_id)
    if not isinstance(expected_state, list):
        expected_state = [expected_state]
    if not isinstance(expected_status, list):
        expected_status = [expected_status]
    if state and state.get('state') in expected_state \
       and state.get('status') in expected_status:
        return True
    return False

@action(namespace='client')
def run_tests(agent):
    agent.connect_server(agent.config['host'], agent.config['port'])
    domain_id = uuid.UUID('39684e0d-6173-4d41-8efe-add8f24dd2cb')
    domain = RPCBrokerProxy(
        agent.server_socket, 'broker_proxy',
        domain_id
    )
    remote_domain = RPCBrokerProxy(
        agent.server_socket, 'broker_domain_proxy',
        domain_id,
        domain_index=0
    )

    try:
        agent.server.domain_start(id=domain_id)
        ensure_domain_state(agent, domain_id, 'blank')
    except RPCException:
        pass
    assert domain.ping.wait() == 'pong'
    assert domain.ping() is None
    assert domain.ping.wait() == 'pong'
    assert domain.ping.no_reply() is None
    agent.server.domain_stop(id=domain_id)

