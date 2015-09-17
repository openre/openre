# -*- coding: utf-8 -*-

from openre.agent.decorators import action
from openre.agent.server.decorators import start_process
from openre.agent.server.helpers import stop_process
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
