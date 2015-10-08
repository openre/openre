# -*- coding: utf-8 -*-
"""
OpenRE.Agent - агент для запуска доменов.
"""
from openre.agent.args import parser
import logging
import os
import importlib

def run():
    args, unknown = parser.parse_known_args()
    mod = None

    # find module by type
    base_dir = os.path.dirname(__file__)
    for sub_dir in sorted([sub_dir for sub_dir in os.listdir(base_dir) \
                          if os.path.isdir('%s/%s' % (base_dir, sub_dir))]):

        if args.type != sub_dir:
            continue
        module_dir = '%s/%s' % (base_dir, sub_dir)
        if os.path.isfile('%s/__init__.py' % module_dir):
            mod = importlib.import_module('openre.agent.%s' % sub_dir)

    if mod:
        mod.run()
    else:
        logging.error('Module not found')


def test_agents():
    import zmq
    from openre.agent.helpers import RPCBroker, Transport, RPC, AgentBase, \
            from_json
    from openre.agent.server import Agent as ServerAgent
    transport = Transport()
    class ServerAgentTest(ServerAgent):
        def init(self):
            self.responder = transport.socket(zmq.ROUTER)
            self.responder.bind("inproc://server-responder")
            self.broker_socket = transport.socket(zmq.DEALER)
            self.broker_socket.RCVTIMEO = 10000
            self.broker_socket.connect("inproc://server-broker")
            self.broker = RPCBroker(self.broker_socket)

    class ClientAgent(AgentBase):
        def init(self):
            self.server_socket = transport.socket(zmq.REQ)
            self.server_socket.connect("inproc://server-responder")
            self.server = RPC(self.server_socket)
    # server
    server_agent = ServerAgentTest({})
    # client
    client_agent = ClientAgent({})

    # client -> server -> client
    client_agent.send_server('ping', {'test': 'ok'}, skip_recv=True)
    message = server_agent.responder.recv_multipart()
    assert len(message) == 4
    print message
    assert message[1] == ''
    assert message[2] == ''
    assert 'action' in message[3]
    data = from_json(message[3])
    assert data['action'] == 'ping'
    assert data['data']['test'] == 'ok'
    address = message[0]
    server_agent.reply(address, 'pong')
    reply_message = client_agent.server_socket.recv()
    reply_data = from_json(reply_message)
    assert reply_data == 'pong'
