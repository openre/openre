# -*- coding: utf-8 -*-
import logging
from functools import wraps
from openre.agent.server.state import process_state, is_running

def start_process(name='process'):
    def wrapper(f):
        @wraps(f)
        def wrapped(event, process_id, wait=True, exit_on_error=False,
                    *args, **kwargs):
            if process_id in process_state:
                state = process_state[process_id]
                if is_running(state):
                    event.failed('%s already running.' % name.capitalize())
                    return

            logging.debug('Start process "%s"' % name)
            process_state[process_id] = {
                'status': 'open',
                'pid': 0,
                'id': process_id,
                'name': name,
            }
            ret = f(event, process_id, *args, **kwargs)
            if wait:
                exit_status = ret.wait()
                # process already running
                if exit_status == 2:
                    logging.critical(
                        '%s already running. Shutdown it first.',
                        name.capitalize()
                    )
                    process_state[process_id] = {
                        'status': 'error',
                        'pid': 0,
                        'message': '%s already running.' % name.capitalize(),
                    }
                    event.failed('%s already running.' % name.capitalize())
                if exit_on_error and exit_status != 0:
                    exit(0)
            return ret
        return wrapped
    return wrapper
