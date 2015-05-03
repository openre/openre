# -*- coding: utf-8 -*-

from openre.agent.decorators import action
from openre.agent.server.state import state as process_state

@action()
def state(event):
    if event.data and event.id:
        process_state[event.id] = event.data
        if process_state[event.id]['id'] is None:
            process_state[event.id] = {'id': event.id}
    if event.id:
        if event.id in process_state:
            return process_state[event.id]
        return event.failed('No such agent id')
    return state_dump(event)

@action()
def state_dump(event):
    return process_state.values()

