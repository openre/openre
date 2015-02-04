# -*- coding: utf-8 -*-
"""
Helper functions and decorators
"""
import cProfile
from functools import wraps

def profileit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        prof = cProfile.Profile()
        retval = prof.runcall(func, *args, **kwargs)
        import pstats
        pstats.Stats(prof).sort_stats('cumulative').print_stats(40)
        return retval
    return wrapper


