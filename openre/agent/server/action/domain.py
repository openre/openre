# -*- coding: utf-8 -*-

from openre.agent.decorators import action
from openre.agent.server.decorators import start_process
from openre.agent.server.helpers import stop_process
from openre.agent.server.state import process_state, is_running
import sys
import subprocess
import os
from openre import BASE_PATH
import uuid
import re

@action()
def domain_start(event):
    data = event.data
    if not isinstance(data, dict):
        data = {}
    # deny run two domains with the same name
    if False:
        name = data.get('name')
        if name:
            name = 'domain.%s' % name
        else:
            name = 'domain'
        for stt in process_state.values():
            if name == stt['name'] and is_running(stt):
                return event.failed(
                    'Processes with name "%s" is already running' % (name,)
                    )
    do_domain_start(
        event,
        str(data.get('id', uuid.uuid4())),
        wait=data.get('wait', True),
        exit_on_error=data.get('exit_on_error', False)
    )

@start_process('domain')
def do_domain_start(event, proccess_id):
    server = event.pool.context['server']
    data = event.data
    if not isinstance(data, dict):
        data = {}
    params = [
        sys.executable,
        os.path.realpath(os.path.join(BASE_PATH, '../openre-agent')),
        'domain',
        'start',
        '--server-host', data.get('server_host', server.config.host),
        '--server-port', data.get('server_port', server.config.port),
        '--id', proccess_id,
        '--pid', '-',
    ]
    if data.get('name'):
        params.extend([
            '--name', data['name']
        ])
    return subprocess.Popen(params)

@action()
def domain_stop(event):
    name = 'domain'
    if isinstance(event.data, basestring):
        if re.search(r'^domain\.', event.data):
            name = event.data
    return stop_process(event, name=name)
