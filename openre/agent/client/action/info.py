# -*- coding: utf-8 -*-

from openre.agent.decorators import action
from openre.device import DEVICES

@action(namespace='client')
def local_devices(agent):
    print DEVICES
