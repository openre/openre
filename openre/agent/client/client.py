# -*- coding: utf-8 -*-
"""
Основной код сервера
"""
from openre.agent.helpers import AgentBase

class Agent(AgentBase):
    def init(self):
        self.connect_server(self.config.host, self.config.port)

    def run(self):
        if self.config.action == 'hello':
            pass
        self.send_server(self.config.action)

    def clean(self):
        pass

