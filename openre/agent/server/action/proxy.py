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
def start_proxy(event):
    server = event.pool.context['server']
    data = event.data
    if not isinstance(data, dict):
        data = {}
    do_start_proxy(
        event,
        str(data.get('id', server.proxy_id)),
        wait=data.get('wait', True),
        exit_on_error=data.get('exit_on_error', False)
    )

@start_process('proxy')
def do_start_proxy(event, proccess_id):
    server = event.pool.context['server']
    data = event.data
    if not isinstance(data, dict):
        data = {}
    proxy_pid = os.path.join(
        tempfile.gettempdir(), 'openre-proxy.pid')
    return subprocess.Popen([
        sys.executable,
        os.path.realpath(os.path.join(BASE_PATH, '../openre-agent')),
        'proxy',
        'start',
        '--host', data.get('host', server.config.proxy_host),
        '--port', data.get('port', server.config.proxy_port),
        '--server-host', data.get('server_host', server.config.host),
        '--server-port', data.get('server_port', server.config.port),
        '--id', proccess_id,
        '--pid', data.get('pid', proxy_pid),
    ])

@action()
def stop_proxy(event):
    return stop_process(event, name='proxy')
