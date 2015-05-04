# -*- coding: utf-8 -*-

from openre.agent.decorators import action
from openre.agent.server.decorators import start_process
from openre.agent.server.helpers import stop_process
import sys
import subprocess
import os
from openre import BASE_PATH
import uuid

@action()
def start_domain(event):
    data = event.data
    if not isinstance(data, dict):
        data = {}
    do_start_domain(
        event,
        str(data.get('id', uuid.uuid4())),
        wait=data.get('wait', True),
        exit_on_error=data.get('exit_on_error', False)
    )

@start_process('domain')
def do_start_domain(event, proccess_id):
    server = event.pool.context['server']
    data = event.data
    if not isinstance(data, dict):
        data = {}
    return subprocess.Popen([
        sys.executable,
        os.path.realpath(os.path.join(BASE_PATH, '../openre-agent')),
        'domain',
        'start',
        '--server-host', data.get('server_host', server.config.host),
        '--server-port', data.get('server_port', server.config.port),
        '--id', proccess_id,
        '--pid', '-',
    ])

@action()
def stop_domain(event):
    return stop_process(event, name='domain')
