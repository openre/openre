# -*- coding: utf-8 -*-
"""
Основной код сервера
"""
from openre.agent.helpers import AgentBase

class Agent(AgentBase):
    def init(self):
        self.connect_server(self.config.host, self.config.port)

    def run(self):
        result = self.send_server(self.config.action)
        if result['success']:
            print result['data']
        else:
            print result['traceback']

    def clean(self):
        pass

