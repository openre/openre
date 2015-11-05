# -*- coding: utf-8 -*-
from functools import wraps

def proxy_call_to_domains(priority=None):
    """
    Запускает точно такую же функцию на всех доменах входящих в сеть
    """
    def wrapper(f):
        @wraps(f)
        def wrapped(net, *args, **kwargs):
            name = f.__name__
            net.set_task(name, state='run')
            try:
                for domain in net.domains:
                    call = getattr(domain, name)
                    if not priority is None:
                        call.set_priority(priority)
                    call(*args, **kwargs)
                f(net, *args, **kwargs)
            except Exception:
                net.set_task(name, state='error')
                raise
            # wait for proper domain state from server
            net.set_task(name, state='success')
        return wrapped
    return wrapper
