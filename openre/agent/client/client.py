# -*- coding: utf-8 -*-
"""
Основной код клиента
"""
from openre.agent.helpers import AgentBase
#import pprint
from openre.agent.helpers import from_json
import os.path
import importlib
from openre.agent.helpers import do_strict_action

class Agent(AgentBase):
    def init(self):
        self.init_actions()
        self.net_config = None
        # FIXME: remove this and next debug code
        self.connect_server(self.config.host, self.config.port)
        import uuid
        from openre.agent.helpers import RPCBrokerProxy
        #self.domain = RPCBrokerProxy(
        #    self.server_socket, 'broker_domain_proxy',
        #    uuid.UUID('4d2f95ad-c6e7-4d66-9eb7-27eb93b5421a'),
        #    domain_index=0
        #)
        self.domain = RPCBrokerProxy(
            self.server_socket, 'broker_proxy',
            uuid.UUID('4d2f95ad-c6e7-4d66-9eb7-27eb93b5421a')
        )

    def run(self):
        if self.config.config and self.config.action == 'run':
            try:
                self.net_config = from_json(self.config.config.read())
            except ValueError as error:
                self.die('JSON is invalid: %s', error)

        result = do_strict_action(self.config.action, 'client', self)
        print result
        """
        result = self.send_server(
            self.config.action,
            self.from_json(self.config.data)
        )
        if result['success']:
            if result['data'] is None:
                print 'Done.'
            elif self.config.pretty:
                pp = pprint.PrettyPrinter(indent=4)
                pp.pprint(result['data'])
            else:
                print result['data']
        else:
            print 'Error: %s' % result['traceback']
        """

    def clean(self):
        pass

    def init_actions(self):
        """
        Load all client actions
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
                'openre.agent.client.action.%s' % action_module_name
            )

