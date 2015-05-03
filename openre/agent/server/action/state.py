# -*- coding: utf-8 -*-

from openre.agent.decorators import action

@action()
def state(event):
    print 'state called'

