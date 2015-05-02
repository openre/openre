# -*- coding: utf-8 -*-
"""
Основной код сервера
"""
import logging
import zmq
from openre.agent.helpers import AgentBase

class Agent(AgentBase):
    def init(self):
        self.responder = self.socket(zmq.ROUTER)
        try:
            self.responder.bind(
                "tcp://%s:%s" % (self.config.host, self.config.port))
        except zmq.error.ZMQError as error:
            if error.errno == 98: # Address already in use
                logging.warn(
                    "Address tcp://%s:%s already in use. Server is already " \
                    "runnning?",
                    self.config.host, self.config.port)
            raise
        self.poller = zmq.Poller()
        self.poller.register(self.responder, zmq.POLLIN)

    def run(self):
        while True:
            socks = dict(self.poller.poll())
            if socks.get(self.responder) == zmq.POLLIN:
                message = self.responder.recv_multipart()
                logging.debug('Received message: %s', message)
                message = [message[0], '', b"World"]
                self.responder.send_multipart(message)
                logging.debug('Reply with message: %s', message)

    def clean(self):
        self.responder.close()

