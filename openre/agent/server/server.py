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
                if len(message) < 3:
                    logging.warn('Broken message: %s', message)
                    continue
                address = message[0]
                data = self.from_json(message[2])
                logging.debug('Received message: %s', data)

                # TODO: event driven message processing
                # add address and data to event pool
                # when event is done - send result to the client
                # pereodically check events untill all done
                # then wait for a new messages

                ret = {'success': True}
                self.reply(address, ret)


    def reply(self, address, data):
        message = [address, '', self.to_json(data)]
        self.responder.send_multipart(message)
        logging.debug('Reply with message: %s', message)


    def clean(self):
        self.responder.close()

