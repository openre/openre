# -*- coding: utf-8 -*-
"""
Загрузка конфига.
"""

from openre.agent.decorators import action
from openre.agent.domain.decorators import state
from openre import OpenRE

@action(namespace='domain')
@state('config')
def config(event, net_config):
    """
    Создаем пустой объект класса OpenRE
    """
    agent = event.pool.context['agent']
    assert 'net' not in agent.context
    agent.context['net'] = OpenRE(net_config)

