# -*- coding: utf-8 -*-

from openre.agent.decorators import action
import logging
from openre.agent.client.helpers import Net

@action(namespace='client')
def run(agent):
    logging.debug('Run Net')
    config = agent.net_config
    if not config:
        raise ValueError('No net config')
    net = Net(config)
    logging.info('Run simulation')
    net.run()

@action(namespace='client')
def info(agent):
    config = agent.net_config
    if not config:
        raise ValueError('No net config')
    net = Net(config)
    ret = ''
    for domain in net.domains:
        stats = domain.domain.stat.wait() or {}
        ret += '%s:' % domain.name
        ret += '\n'
        for key in sorted(stats.keys()):
            ret += '    %s %s' % (key, stats[key])
            ret += '\n'
        ret += "    events count: %s" % domain.broker.events\
                .set_priority(2000000).wait()
        ret += '\n'
    return ret

@action(namespace='client')
def destroy(agent):
    config = agent.net_config
    if not config:
        raise ValueError('No net config')
    net = Net(config)
    logging.info('Destroying Net')
    net.destroy()
    net.clean()

@action(namespace='client')
def start(agent):
    config = agent.net_config
    if not config:
        raise ValueError('No net config')
    net = Net(config)
    logging.info('Resume simulation')
    net.start()

@action(namespace='client')
def pause(agent):
    config = agent.net_config
    if not config:
        raise ValueError('No net config')
    net = Net(config)
    logging.info('Pause simulation')
    net.pause()

@action(namespace='client')
def stop(agent):
    config = agent.net_config
    if not config:
        raise ValueError('No net config')
    net = Net(config)
    logging.info('Stop simulation')
    net.stop()

