# -*- coding: utf-8 -*-
import os
from openre.agent.server.state import process_state, is_running
import uuid
import signal
import logging

def stop_process(event, name=None):
    """
    If name is not None, than check that state have the same name
    """
    pid = event.context.get('id', event.data)
    state = None
    if isinstance(pid, uuid.UUID) or str(pid) in process_state:
        state = process_state[str(pid)]
        pid = state['pid']
    elif isinstance(pid, int):
        for st in process_state.values():
            if st['pid'] == pid:
                state = st
                break
    elif pid is None and name:
        for st in process_state.values():
            if st['name'] == name:
                state = st
                pid = state['pid']
                break

    # first run
    if 'id' not in event.context:
        event.context['id'] = state['id']
        if not is_running(state):
            return event.failed('%s already stopped.' % name.capitalize())
        if not isinstance(pid, int) or not pid:
            return event.failed('Wrong pid format %s' % repr(pid))
    if not state:
        return event.failed('Process state not found for "%s", cant kill' % pid)
    if name and state['name'] != name:
        return event.failed(
            'Process state name "%s" not equal "%s", cant kill' % (
                state['name'], name))

    if state['status'] not in ['exit', 'error', 'kill', 'clean']:
        try:
            os.kill(pid, signal.SIGTERM)
            logging.debug('Kill %s' % pid)
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
                    'Process with pid %s stopped with errors' % pid)
            else:
                logging.debug(
                    'Successfully stopped process with pid %s' % pid)
            return
        event.timeout(1)
