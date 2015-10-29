# -*- coding: utf-8 -*-
from functools import wraps

def proxy_call_to_domains(f):
    """
    Запускает точно такую же функцию на всех доменах входящих в сеть
    """
    @wraps(f)
    def wrapped(net, *args, **kwargs):
        name = f.__name__
        net.set_task(name, state='run')
        try:
            for domain in net.domains:
                getattr(domain, name)(*args, **kwargs)
            f(net, *args, **kwargs)
        except Exception:
            net.set_task(name, state='error')
            raise
        # wait for proper domain state from server
        net.set_task(name, state='success')
    return wrapped


