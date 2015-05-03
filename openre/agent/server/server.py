# -*- coding: utf-8 -*-
"""
Основной код сервера
"""
import logging
import zmq
from openre.agent.helpers import AgentBase
import os
import importlib
from openre.agent.helpers import do_action
from openre.agent.event import EventPool, ServerEvent

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
        self.init_actions()

    def run(self):
        poll_timeout = -1
        def event_done(event):
            if not event.address:
                return
            if event.is_success:
                ret = {
                    'success': event.is_success,
                    'data': event.result
                }
            else:
                ret = {
                    'success': event.is_success,
                    'data': event.result,
                    'error': event.error,
                    'traceback': event.traceback
                }

            self.reply(event.address, ret)
        event_pool = EventPool()
        while True:
            socks = dict(self.poller.poll(poll_timeout))
            if socks.get(self.responder) == zmq.POLLIN:
                message = self.responder.recv_multipart()
                if len(message) < 3:
                    logging.warn('Broken message: %s', message)
                    continue
                address = message[0]
                data = self.from_json(message[2])
                logging.debug('Received message: %s', data)

                if not isinstance(data, dict) or 'action' not in data:
                    logging.warn(
                        'Malformed data in message ' \
                        '(should be dict with \'action\' key): %s', data)
                    ret = {
                        'success': False,
                        'data': None,
                        'error': 'Malformed message: %s' % data,
                        'traceback': 'Malformed message: %s' % data
                    }
                    self.reply(address, ret)
                    continue

                event = ServerEvent(data['action'], data, address)
                event.done_callback(event_done)
                event_pool.register(event)
            event_pool.tick()
            # if no events - than wait for new events without timeout
            poll_timeout = event_pool.poll_timeout()
            if poll_timeout >= 0 and poll_timeout < 100:
                poll_timeout = 100

    def reply(self, address, data):
        message = [address, '', self.to_json(data)]
        self.responder.send_multipart(message)
        logging.debug('Reply with message: %s', message)

    def clean(self):
        self.responder.close()

    def init_actions(self):
        # find module by type
        base_dir = os.path.dirname(__file__)
        base_dir = os.path.join(base_dir, 'action')
        for action_file in sorted(
            [file_name for file_name in os.listdir(base_dir) \
             if os.path.isfile('%s/%s' % (base_dir, file_name))
                and file_name not in ['__init__.py']]
        ):
            action_module_name = action_file.split('.')
            del action_module_name[-1]
            action_module_name = '.'.join(action_module_name)
            importlib.import_module(
                'openre.agent.server.action.%s' % action_module_name
            )

