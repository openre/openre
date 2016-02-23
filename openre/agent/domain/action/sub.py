# -*- coding: utf-8 -*-
"""
Get data from sub channel
"""
from openre.agent.decorators import action


@action(namespace='domain')
def NP(agent, layer_index, packet):
    """
    Process numpy data from network
    """
    agent.context['local_domain'].stat_inc('receive_data')
    agent.context['local_domain'].register_input_layer_data(
        int(layer_index), packet)
