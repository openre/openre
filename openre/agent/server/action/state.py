# -*- coding: utf-8 -*-

from openre.agent.decorators import action

@action(namespace='server')
def process_state(event):
    _process_state = event.pool.context['server'].process_state
    if event.data and event.id:
        if 'pid' in event.data:
            if event.data['pid'] != 0:
                event.data['was_pid'] = event.data['pid']
        _process_state[event.id] = event.data
        if _process_state[event.id]['id'] is None:
            _process_state[event.id] = {'id': event.id}
    if event.id:
        if event.id in _process_state:
            return _process_state[event.id]
        return event.failed('No such agent id')
    return process_state_dump(event)

@action(namespace='server')
def process_state_dump(event):
    _process_state = event.pool.context['server'].process_state
    return _process_state.values()

@action(namespace='server')
def domain_state(event, id=None):
    _domain_state = event.pool.context['server'].domain_state
    if event.data and event.id:
        _domain_state[event.id] = event.data
        if _domain_state[event.id]['id'] is None:
            _domain_state[event.id] = {'id': event.id}
    if id:
        if id in _domain_state:
            return _domain_state[id]
        return {}
    if event.id:
        if event.id in _domain_state:
            return _domain_state[event.id]
        return event.failed('No such agent id')
    return domain_state_dump(event)

@action(namespace='server')
def domain_state_dump(event):
    _domain_state = event.pool.context['server'].domain_state
    return _domain_state.values()

