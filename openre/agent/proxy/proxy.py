# -*- coding: utf-8 -*-
"""
Основной код прокси
"""
import logging
import zmq
import tempfile
import os
from openre.agent.helpers import AgentBase

class Agent(AgentBase):
    server_connect = True
    def init(self):
        # Socket facing clients
        self.frontend = self.socket(zmq.SUB)
        try:
            self.frontend.bind(
                "tcp://%s:%s" % (self.config.host, self.config.port)
            )
        except zmq.error.ZMQError as error:
            if error.errno == 98: # Address already in use
                logging.warn(
                    "Address tcp://%s:%s already in use. Proxy is already " \
                    "runnning?",
                    self.config.host, self.config.port)
            raise

        self.frontend.setsockopt(zmq.SUBSCRIBE, "")

        # Socket facing services
        ipc_file = os.path.join(tempfile.gettempdir(), 'openre-proxy')
        self.backend = self.socket(zmq.PUB)
        self.backend.bind("ipc://%s" % ipc_file)


    def run(self):
        zmq.device(zmq.FORWARDER, self.frontend, self.backend)

    def clean(self):
        self.frontend.close()
        self.backend.close()

