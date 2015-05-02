# -*- coding: utf-8 -*-
"""
Основной код сервера
"""
import zmq
import logging
from openre.agent.helpers import AgentBase

class Agent(AgentBase):
    def init(self):
        self.requester = self.socket(zmq.REQ)
        self.requester.connect(
            "tcp://%s:%s" % (self.config.host, self.config.port))

    def run(self):
        if self.config.action == 'hello':
            self.hello()

    def clean(self):
        self.requester.close()

    def hello(self):
        message = b'Hello'
        logging.debug("Send message: %s", message)
        self.requester.send(message)
        message = self.requester.recv()
        logging.debug("Received reply: %s", message)
