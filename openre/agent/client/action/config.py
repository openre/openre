# -*- coding: utf-8 -*-
"""
Обработка конфигурационных файлов
"""
from openre.agent.decorators import action
import logging
from openre.agent.client.helpers import prepare_config
from openre.agent.helpers import to_json


@action(namespace='client')
def config(agent):
    logging.debug('Prepare config')
    config = agent.net_config
    if not config:
        raise ValueError('No net config')
    prepare_config(config)
    config = to_json(config)
    if agent.config['out']:
        agent.config['out'].write(config)
    else:
        print config


