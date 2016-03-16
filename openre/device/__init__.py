# -*- coding: utf-8 -*-

from openre.device.abstract import Device
import os
import importlib
import inspect
from openre.templates import TEMPLATES_LOCATIONS
import logging
from openre.helpers import DEVICES


def find_in_module(module):
    module_full_name = module.__name__
    TEMPLATES_LOCATIONS.add(module_full_name)
    devices = []
    for attr_name in dir(module):
        if attr_name[0:2] == '__' or attr_name in ['Device']:
            continue
        attr = getattr(module, attr_name)
        if not inspect.isclass(attr):
            continue
        if issubclass(attr, Device):
            globals().update({attr_name: attr})
            devices.append(attr_name)

    if devices:
        DEVICES.import_success(module_full_name, devices)

def find_in_dir(base_dir, module_prefix=''):

    for module_file in sorted(
        [file_name for file_name in os.listdir(base_dir) \
         if ((os.path.isfile('%s/%s' % (base_dir, file_name)) \
              and file_name[-3:] == '.py') \
             or os.path.isfile('%s/%s/__init__.py' % (base_dir, file_name)))
            and file_name not in ['__init__.py', 'abstract.py']]
    ):
        module_name = module_file.split('.')
        if module_name[-1] == 'py':
            del module_name[-1]
        module_name = '.'.join(module_name)
        module_full_name = '%s%s' % (module_prefix, module_name)
        try:
            module = importlib.import_module(module_full_name)
            find_in_module(module)
        except ImportError as err:
            logging.debug(
                'Module %s not imported, so devices from this module will not' \
                ' be available. Error: %s',
                module_full_name,
                str(err)
            )
            DEVICES.import_error(module_full_name, str(err))
            continue


find_in_dir(os.path.dirname(__file__), 'openre.device.')
