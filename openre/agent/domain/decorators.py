# -*- coding: utf-8 -*-
from functools import wraps
import traceback

def state(name):
    """
    Устанавливает статус и состояние домена в зависимости от результата
    выполнения декорируемой функции
    """
    def wrapper(f):
        @wraps(f)
        def wrapped(event, *args, **kwargs):
            agent = event.pool.context['agent']
            agent.send_server('domain_state', {
                'state': name,
                'status': 'running',
            })

            try:
                ret = f(event, *args, **kwargs)
            except Exception:
                agent.send_server('domain_state', {
                    'state': name,
                    'status': 'error',
                    'message': traceback.format_exc()
                })
                raise

            agent.send_server('domain_state', {
                'state': name,
                'status': 'done',
            })
            return ret
        return wrapped
    return wrapper


