# -*- coding: utf-8 -*-
"""
Запуск моделирования, остановка и пауза сети.
"""

from openre.agent.decorators import action
from openre.agent.domain.decorators import state


@action(namespace='domain')
@state('run')
def run(event):
    """
    Запуск моделирования
    """
    agent = event.pool.context['agent']
    net = agent.context['net']
    net.tick()
    if not net.is_stop:
        net.is_stop = False
        event.prevent_done()

@action(namespace='domain')
def pause(event):
    """
    Ставим моделирование на паузу
    """
    agent = event.pool.context['agent']
    net = agent.context['net']
    agent.send_server('domain_state', {
        'state': 'run',
        'status': 'pause',
    })
    return net.pause()

@action(namespace='domain')
def start(event):
    """
    Запускаем, если ставили на паузу
    """
    agent = event.pool.context['agent']
    net = agent.context['net']
    agent.send_server('domain_state', {
        'state': 'run',
        'status': 'running',
    })
    return net.start()

@action(namespace='domain')
def stop(event):
    """
    Останавливаем моделирование. При этом event 'run' завершается.
    Для повторного запуска надо заново запускать event 'run'.
    """
    agent = event.pool.context['agent']
    net = agent.context['net']
    agent.send_server('domain_state', {
        'state': 'run',
        'status': 'done',
    })
    return net.stop()


