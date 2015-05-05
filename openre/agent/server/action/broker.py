# -*- coding: utf-8 -*-
from openre.agent.decorators import action
from openre.agent.server.decorators import start_process
from openre.agent.server.helpers import stop_process
import sys
import subprocess
import os
from openre import BASE_PATH
import tempfile

@action()
def broker_start(event):
    server = event.pool.context['server']
    data = event.data
    if not isinstance(data, dict):
        data = {}
    do_broker_start(
        event,
        str(data.get('id', server.broker_id)),
        wait=data.get('wait', True),
        exit_on_error=data.get('exit_on_error', False)
    )

@start_process('broker')
def do_broker_start(event, process_id):
    server = event.pool.context['server']
    data = event.data
    if not isinstance(data, dict):
        data = {}
    broker_pid = os.path.join(
        tempfile.gettempdir(), 'openre-broker.pid')
    return subprocess.Popen([
        sys.executable,
        os.path.realpath(os.path.join(BASE_PATH, '../openre-agent')),
        'broker',
        'start',
        '--id', process_id,
        '--pid', data.get('pid', broker_pid),
        '--server-host', data.get('server_host', server.config.host),
        '--server-port', data.get('server_port', server.config.port),
    ])

@action()
def broker_stop(event):
    return stop_process(event, name='broker')
