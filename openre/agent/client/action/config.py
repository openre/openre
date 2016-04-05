# -*- coding: utf-8 -*-
"""
Обработка конфигурационных файлов
"""
from openre.agent.decorators import action
import logging
from openre.config import Config
from openre.helpers import to_json


@action(namespace='client')
def config(agent):
    logging.debug('Prepare config')
    config = agent.net_config
    if not config:
        raise ValueError('No net config')
    config = Config(config)
    config.make_unique()
    if agent.config['out']:
        agent.config['out'].write(to_json(config))
    return config
