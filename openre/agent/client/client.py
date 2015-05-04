# -*- coding: utf-8 -*-
"""
Основной код сервера
"""
from openre.agent.helpers import AgentBase
import pprint

class Agent(AgentBase):
    def init(self):
        self.connect_server(self.config.host, self.config.port)

    def run(self):
        result = self.send_server(
            self.config.action,
            self.from_json(self.config.data)

        )
        if result['success']:
            if not result['data']:
                print 'Done.'
            elif self.config.pretty:
                pp = pprint.PrettyPrinter(indent=4)
                pp.pprint(result['data'])
            else:
                print result['data']
        else:
            print 'Error: %s' % result['traceback']

    def clean(self):
        pass

