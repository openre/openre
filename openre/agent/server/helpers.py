# -*- coding: utf-8 -*-
import os
from openre.agent.server.state import is_running
import uuid
import signal
import logging

def stop_process(event, name=None, id=None):
    """
    If name is not None, than check that state have the same name
    """
    # on the second run pid is already in event.context['id']
    pid = event.context.get('id', id)
    state = None
    process_state = event.pool.context['server'].process_state
    def is_proper_name(name, state_name):
        if not name:
            return False
        if '.' not in name and '.' in state_name \
           and state_name.startswith('%s.' % name):
            return True
        if name == state_name:
            return True
        return False
    if isinstance(pid, uuid.UUID) or str(pid) in process_state:
        state = process_state[str(pid)]
        pid = state['pid']
    elif isinstance(pid, int):
        for stt in process_state.values():
            if stt['pid'] == pid:
                state = stt
                break
    elif name:
        rows = []
        for stt in process_state.values():
            if is_proper_name(name, stt['name']) and stt['pid']:
                state = stt
                rows.append(stt)
                pid = state['pid']
        if len(rows) > 1:
            command = ''
            for row in rows:
                command += '%s (status: %s)\n' % (row['pid'], row['status'])
            return event.failed(
                'There are %s processes with name "%s".' \
                ' Specify which one to stop:\n%s'
                % (len(rows), name, command)
            )

    if not state:
        return event.failed(
            'Process state not found for name="%s", id="%s", cant kill'
            % (name, pid))
    # first run of the task
    if 'id' not in event.context:
        event.context['id'] = state['id']
        if not is_running(state):
            return event.failed('%s already stopped.' % name.capitalize())
        if not isinstance(pid, int) or not pid:
            return event.failed('Wrong pid format %s' % repr(pid))

    if not is_proper_name(name, state['name']):
        return event.failed(
            'Process state name "%s" not equal "%s", cant kill' % (
                state['name'], name))

    if state['status'] not in ['exit', 'error', 'kill', 'clean']:
        try:
            os.kill(pid, signal.SIGTERM)
            logging.debug('Kill %s', pid)
            process_state[str(state['id'])] = {
                'status': 'kill',
            }
            event.expire(600)
        except OSError:
            process_state[str(state['id'])] = {
                'status': 'error',
                'message': 'Exit but not properly cleaned',
                'pid': 0,
            }
            return
    if state['status'] in ['kill', 'clean']:
        try:
            os.kill(pid, 0)
        except OSError:  #No process with locked PID
            # exception while cleaning
            if state['status'] == 'clean':
                process_state[str(state['id'])] = {
                    'status': 'error',
                    'message': 'Exit but not properly cleaned',
                    'pid': 0,
                }
                logging.warn(
                    'Process with pid %s stopped with errors', pid)
            else:
                logging.debug(
                    'Successfully stopped process with pid %s', pid)
            return
        event.timeout(1)
