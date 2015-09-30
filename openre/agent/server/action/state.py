# -*- coding: utf-8 -*-

from openre.agent.decorators import action
from openre.agent.server.state import process_state as _process_state
from openre.agent.server.state import domain_state as _domain_state

@action()
def process_state(event):
    if event.data and event.id:
        _process_state[event.id] = event.data
        if _process_state[event.id]['id'] is None:
            _process_state[event.id] = {'id': event.id}
    if event.id:
        if event.id in _process_state:
            return _process_state[event.id]
        return event.failed('No such agent id')
    return process_state_dump(event)

@action()
def process_state_dump(event):
    return _process_state.values()

@action()
def domain_state(event, id=None):
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

@action()
def domain_state_dump(event):
    return _domain_state.values()

