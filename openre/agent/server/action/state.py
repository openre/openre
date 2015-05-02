# -*- coding: utf-8 -*-

from openre.agent.decorators import action

@action()
def state():
    print 'state called'

