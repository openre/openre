# -*- coding: utf-8 -*-
"""
Загрузка конфига.
"""

from openre.agent.decorators import action
from openre.agent.domain.decorators import state
from openre import OpenRE

@action()
@state('config')
def config(event, net_config, local_domains=None):
    """
    Создаем пустой объект класса OpenRE и указываем какие домены будут
    локальными.
    net_config - конфиг сети
    local_domains - список имен доменов в конфиге, которые будут моделироваться
        локально
    """
    agent = event.pool.context['agent']
    assert 'net' not in agent.context
    agent.context['net'] = OpenRE(net_config, local_domains=local_domains)

