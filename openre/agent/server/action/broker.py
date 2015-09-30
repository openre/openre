# -*- coding: utf-8 -*-
from openre.agent.decorators import action
from openre.agent.server.decorators import start_process
from openre.agent.server.helpers import stop_process
import sys
import subprocess
import os
from openre import BASE_PATH
import tempfile
import uuid

@action()
def broker_start(event, wait=True, exit_on_error=False, id=None, pid=None,
                 server_host=None, server_port=None,
                ):
    server = event.pool.context['server']
    do_broker_start(
        event,
        str(id or server.broker_id),
        wait=wait,
        exit_on_error=exit_on_error,
        server_host=server_host,
        server_port=server_port,
        pid=pid
    )

@start_process('broker')
def do_broker_start(event, process_id,
                    server_host=None, server_port=None,
                    pid=None
                   ):
    server = event.pool.context['server']
    if not pid:
        pid = os.path.join(
            tempfile.gettempdir(), 'openre-broker.pid')
    return subprocess.Popen([
        sys.executable,
        os.path.realpath(os.path.join(BASE_PATH, '../openre-agent')),
        'broker',
        'start',
        '--id', process_id,
        '--pid', pid,
        '--server-host', server_host or server.config.host,
        '--server-port', server_port or server.config.port,
    ])

@action()
def broker_stop(event, name='broker'):
    return stop_process(event, name=name)

@action()
def broker_proxy(event, *args, **kwargs):
    """
    Прокси метод - отправляет входящее сообщение воркеру через брокера.
    Этот метод вызываетя из объекта класса
    RPCBrokerProxy(socket, 'broker_proxy', broker_address)
    """
    agent = event.pool.context['server']
    event.prevent_done()
    if 'event_id' in event.context:
        return
    event.context['event_id'] = uuid.uuid4()
    event.expire(10)
    # address == proccess_state[i]['id']
    address = event.message['address']
    data = event.data
    args = [(), {}]
    if 'args' in data:
        args = [data['args']['args'], data['args']['kwargs']]
    return getattr(
        agent.broker.set_address(address) \
            .set_response_address(event.context['event_id']),
        data['action']
    )(*args[0], **args[1])

@action()
def broker_domain_proxy(event, domain_index):
    """
    Прокси метод - отправляет входящее сообщение в домен с учетом domain_index
    через брокера.
    Этот метод вызываетя из объекта класса
    RPCBrokerProxy(socket, 'broker_domain_proxy', broker_address, domain_index)
    """
    agent = event.pool.context['server']
    event.prevent_done()
    if 'event_id' in event.context:
        return
    event.context['event_id'] = uuid.uuid4()
    event.expire(10)
    # address == proccess_state[i]['id']
    address = event.message['address']
    return agent.broker \
            .set_address(address) \
            .set_response_address(event.context['event_id']) \
            .domain_proxy(event.data, domain_index)
