# -*- coding: utf-8 -*-

from openre.agent.decorators import action
from openre.device import DEVICES
from copy import deepcopy

@action(namespace='client')
def local_devices(agent):
    return deepcopy(DEVICES)
