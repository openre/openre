# -*- coding: utf-8 -*-

from openre.agent.decorators import action
from openre.agent.server.decorators import start_process
from openre.agent.server.helpers import stop_process
import sys
import subprocess
import os
from openre import BASE_PATH
import tempfile

@action(namespace='server')
def proxy_start(event, wait=True, exit_on_error=False, id=None,
                host=None, port=None,
                server_host=None, server_port=None,
                pid=None
               ):
    server = event.pool.context['server']
    do_proxy_start(
        event,
        str(id or server.proxy_id),
        wait=wait,
        exit_on_error=exit_on_error,
        host=host,
        port=port,
        server_host=server_host,
        server_port=server_port,
        pid=pid
    )

@start_process('proxy')
def do_proxy_start(event, proccess_id,
                   host=None, port=None,
                   server_host=None, server_port=None,
                   pid=None
                  ):
    server = event.pool.context['server']
    if pid is None:
        pid = os.path.join(
            tempfile.gettempdir(), 'openre-proxy.pid')
    return subprocess.Popen([
        sys.executable,
        os.path.realpath(os.path.join(BASE_PATH, '../openre-agent')),
        'proxy',
        'start',
        '--host', host or server.config['proxy_host'],
        '--port', port or server.config['proxy_port'],
        '--server-host', server_host or server.config['host'],
        '--server-port', server_port or server.config['port'],
        '--id', proccess_id,
        '--pid', pid,
    ])

@action(namespace='server')
def proxy_stop(event):
    return stop_process(event, name='proxy')
