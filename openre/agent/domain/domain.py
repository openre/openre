# -*- coding: utf-8 -*-
"""
Основной код сервера доменов
"""

import zmq
import tempfile
import os
from openre.agent.helpers import AgentBase
import logging

class Agent(AgentBase):
    server_connect = True
    def init(self):
        # Socket facing services
        ipc_broker_file = os.path.join(
            tempfile.gettempdir(), 'openre-broker-backend')
        self.backend = self.socket(zmq.ROUTER)
        self.backend.setsockopt(zmq.IDENTITY, self.id.bytes)
        self.backend.connect("ipc://%s" % ipc_broker_file)

#        ipc_pub_file = os.path.join(
#            tempfile.gettempdir(), 'openre-proxy')
#        self.pub = self.socket(zmq.PUB)
#        self.pub.connect("ipc://%s" % ipc_pub_file)

        self.sub = self.socket(zmq.SUB)
        self.sub.setsockopt(zmq.SUBSCRIBE, self.id.bytes)

        self.poller = zmq.Poller()
        self.poller.register(self.backend, zmq.POLLIN)
        self.poller.register(self.sub, zmq.POLLIN)

    def run(self):
        # main loop
        while True:
            # receive all messages in while loop
            while True:
                socks = dict(self.poller.poll())
                if not socks:
                    break
                if socks.get(self.backend) == zmq.POLLIN:
                    data = self.backend.recv_multipart()
                    logging.debug("in: %s", data)
                    message = [data[0], '', data[2], b'world']
                    self.backend.send_multipart(message)
                    logging.debug("out: %s", message)
                if socks.get(self.sub) == zmq.POLLIN:
                    data = self.sub.recv_multipart()
                    logging.debug("sub in: %s", data)
                    # TODO: process data

    def clean(self):
        self.backend.close()
        self.pub.close()
        self.sub.close()

