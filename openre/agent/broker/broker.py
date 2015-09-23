# -*- coding: utf-8 -*-
"""
Основной код брокера
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
        self.frontend = self.socket(zmq.ROUTER)
        ipc_frontend_file = os.path.join(
            tempfile.gettempdir(), 'openre-broker-frontend')
        self.frontend.bind("ipc://%s" % ipc_frontend_file)

        # Socket facing services
        ipc_backend_file = os.path.join(
            tempfile.gettempdir(), 'openre-broker-backend')
        self.backend = self.socket(zmq.ROUTER)
        self.backend.bind("ipc://%s" % ipc_backend_file)

        self.poller = zmq.Poller()
        self.poller.register(self.frontend, zmq.POLLIN)
        self.poller.register(self.backend, zmq.POLLIN)

    def run(self):
        while True:
            socks = dict(self.poller.poll())
            if socks.get(self.frontend) == zmq.POLLIN:
                message = self.frontend.recv_multipart()
                logging.debug('Frontend receive message: %s', message)
                if len(message) < 3:
                    logging.warn('Invalid message from frontend: %s', message)
                    continue
                req_identity = message[0]
                rep_identity = message[2]
                message[0] = rep_identity
                message[2] = req_identity
                self.backend.send_multipart(message)
                logging.debug('And send to backend: %s', message)
            if socks.get(self.backend) == zmq.POLLIN:
                message = self.backend.recv_multipart()
                logging.debug('Backend receive message: %s', message)
                if len(message) < 3:
                    logging.warn('Invalid message from backend: %s', message)
                    continue
                rep_identity = message[0]
                req_identity = message[2]
                message[0] = req_identity
                message[2] = rep_identity
                self.frontend.send_multipart(message)
                logging.debug('And send to frontend: %s', message)

    def clean(self):
        self.frontend.close()
        self.backend.close()

