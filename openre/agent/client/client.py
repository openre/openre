# -*- coding: utf-8 -*-
"""
Основной код клиента
"""
from openre.agent.helpers import AgentBase
#import pprint
from openre.helpers import from_json
import os.path
import importlib
from openre.agent.helpers import do_strict_action

class Agent(AgentBase):
    def init(self):
        self.init_actions()
        self.net_config = None
        if self.config['config']:
            json_data = None
            if isinstance(self.config['config'], basestring):
                if os.path.isfile(self.config['config']):
                    with open(self.config['config'], 'r') as inf:
                        json_data = inf.read()
                else:
                    json_data = self.config['config']
            elif isinstance(self.config['config'], dict):
                json_data = self.config['config']
            else:
                json_data = self.config['config'].read()
            if isinstance(json_data, dict):
                self.net_config = json_data
            else:
                self.net_config = from_json(json_data)

    def run(self):
        result = do_strict_action(self.config['action'], 'client', self)
        if result is not None:
            print result
        """
        result = self.send_server(
            self.config['action'],
            self.from_json(self.config['data'])
        )
        if result['success']:
            if result['data'] is None:
                print 'Done.'
            elif self.config['pretty']:
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

