# -*- coding: utf-8 -*-

from openre.agent.decorators import action
import logging
from openre.agent.client.helpers import Net

@action(namespace='client')
def deploy(agent):
    logging.debug('Run Net')
    config = agent.net_config
    if not config:
        raise ValueError('No net config')
    net = None
    try:
        logging.info('Creating Net')
        net = Net(config)
        net.create()
        net.upload_config()
        net.deploy_domains()
        net.deploy_layers()
        net.deploy_neurons()
        net.pre_deploy_synapses()
        logging.info('Start creating neurons and synapses.' \
                     ' This may take a while.')
        net.deploy_synapses()
        logging.info('Upload data to devices')
        net.post_deploy_synapses()
        net.post_deploy()
        logging.info('Deploy done')
    except:
        if net:
            logging.info('Destroying Net')
            net.destroy()
            net.clean()
        raise
