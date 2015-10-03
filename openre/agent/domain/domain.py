# -*- coding: utf-8 -*-
"""
Основной код сервера доменов
"""

import zmq
import tempfile
import os
from openre.agent.helpers import AgentBase
import logging
import importlib
from openre.agent.event import EventPool, DomainEvent

class Agent(AgentBase):
    server_connect = True
    def init(self):
        self.init_actions()
        # Socket facing services
        ipc_broker_file = os.path.join(
            tempfile.gettempdir(), 'openre-broker-backend')
        self.backend = self.socket(zmq.ROUTER)
        self.backend.setsockopt(zmq.IDENTITY, bytes(self.id.bytes))
        self.backend.connect("ipc://%s" % ipc_broker_file)

        ipc_pub_file = os.path.join(
            tempfile.gettempdir(), 'openre-proxy')
        self.pub = self.socket(zmq.PUB)
        self.pub.connect("ipc://%s" % ipc_pub_file)

        self.sub = self.socket(zmq.SUB)
        self.sub.setsockopt(zmq.SUBSCRIBE, self.id.bytes)

        self.poller = zmq.Poller()
        self.poller.register(self.backend, zmq.POLLIN)
        self.poller.register(self.sub, zmq.POLLIN)

        self.context = {}

    def run(self):
        def event_done(event):
            # if we don't need the result of the event
            if not event.data.get('wait'):
                return
            if event.is_success:
                ret = {
                    'success': event.is_success,
                    'data': event.result
                }
            else:
                logging.warn(event.traceback)
                ret = {
                    'success': event.is_success,
                    'data': event.result,
                    'error': event.error,
                    'traceback': event.traceback
                }

            if event.data.get('context'):
                ret['context'] = data['context']
            self.reply(event.address, ret)
        poll_timeout = 0
        event_pool = EventPool()
        event_pool.context['agent'] = self

        self.send_server('domain_state', {
            'state': 'blank',
            'status': 'done',
            'name': self.config.name
        })

        process_name = self.config.name
        if not process_name:
            process_name = 'domain'
        if process_name != 'domain':
            process_name = 'domain.%s' % self.config.name
        self.send_server('process_state', {
            'name':  process_name
        })
        # main loop
        while True:
            # receive all messages in while loop
            while True:
                socks = dict(self.poller.poll(poll_timeout))
                if not socks:
                    break
                if socks.get(self.backend) == zmq.POLLIN:
                    message = self.backend.recv_multipart()
                    logging.debug("in: %s", message)
                    data = self.from_json(message[3])
                    address = [message[0], '', message[2]]
                    if not isinstance(data, dict) or 'action' not in data:
                        logging.warn(
                            'Malformed data in message ' \
                            '(should be dict with \'action\' key): %s', data)
                        ret = {
                            'success': False,
                            'data': None,
                            'error': 'Malformed message: %s' % message,
                            'traceback': 'Malformed message: %s' % message
                        }
                        self.reply(address, ret)
                    else:
                        event = DomainEvent(data['action'], 'domain', data,
                                            address)
                        event.done_callback(event_done)
                        event_pool.register(event)
                        # send response immediately
                        if not data.get('wait'):
                            ret = {
                                'success': True,
                                'data': None,
                            }
                            if event.data.get('context'):
                                ret['context'] = data['context']
                            self.reply(address, ret)

                if socks.get(self.sub) == zmq.POLLIN:
                    message = self.sub.recv_multipart()
                    logging.debug("sub in: %s", message)
                    # TODO: process message
                event_pool.tick()
                # if no events - than wait for new events without timeout
                poll_timeout = event_pool.poll_timeout()
                if poll_timeout >= 0 and poll_timeout < 100:
                    poll_timeout = 100

    def reply(self, address, data):
        reply = address + [self.to_json(data)]
        self.backend.send_multipart(reply)
        logging.debug('Reply with message: %s', reply)

    def clean(self):
        self.backend.close()
        self.pub.close()
        self.sub.close()

    def init_actions(self):
        """
        Load all domain actions
        """
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
                'openre.agent.domain.action.%s' % action_module_name
            )

