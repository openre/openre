# -*- coding: utf-8 -*-

from openre.agent.decorators import action
from openre.agent.server.decorators import start_process
from openre.agent.server.helpers import stop_process
from openre.agent.server.state import is_running
import sys
import subprocess
import os
from openre import BASE_PATH
import uuid
import re

@action(namespace='server')
def domain_start(
    event, name=None, id=None, wait=True, exit_on_error=False,
    server_host=None, server_port=None
):
    if id is None:
        id = uuid.uuid4()
    # deny run two domains with the same name
    if False:
        process_state = event.pool.context['server'].process_state
        for stt in process_state.values():
            if name == stt['name'] and is_running(stt):
                return event.failed(
                    'Processes with name "%s" is already running' % (name,)
                    )
    do_domain_start(
        event,
        str(id),
        wait=wait,
        exit_on_error=exit_on_error,
        server_host=server_host,
        server_port=server_port,
        name=name
    )
    return True

@start_process('domain')
def do_domain_start(event, process_id,
                    server_host=None, server_port=None,
                    name=None
                   ):
    server = event.pool.context['server']
    params = [
        sys.executable,
        os.path.realpath(os.path.join(BASE_PATH, 'bin/openre-agent')),
        'domain',
        'start',
        '--server-host', server_host or server.config['host'],
        '--server-port', server_port or server.config['port'],
        '--id', process_id,
        '--pid', '-',
    ]
    if name:
        params.extend([
            '--name', name
        ])
    if server.config['log_level']:
        params.extend([
            '--log-level', server.config['log_level'],
        ])
        # FIXME: store logs in the proper path
        base_dir = os.getcwd()
        if not os.access(base_dir, os.W_OK):
            import tempfile
            base_dir = tempfile.gettempdir()
        log_file_name = os.path.join(
                base_dir, 'openre.domain.%s.log' % (name or str(process_id))
        )
        log_file = open(log_file_name, 'a')
        log_file.write(
            'Server starting domain %s, %s\n' % (name, str(process_id)))
        log_file.flush()
        return subprocess.Popen(
            params, stdout=log_file, stderr=log_file, close_fds=True
        )
    return subprocess.Popen(params)

@action(namespace='server')
def domain_stop(event, name='domain', id=None):
    if name:
        if not re.search(r'^domain\.', name):
            name = 'domain'
    return stop_process(event, name=name, id=id)



