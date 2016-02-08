# content of conftest.py
import os
import importlib
import logging

base_dir = os.path.join(os.path.dirname(__file__), 'openre/device')
collect_ignore = []

# Ignore openre.devices with ImportError exception
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
    try:
        module = importlib.import_module(
            'openre.device.%s' % module_name
        )
    except ImportError as err:
        logging.debug(
            'Module %s not imported, so devices from this module will not be ' \
            'available. Error: %s',
            'openre.device.%s' % module_name,
            str(err)
        )
        collect_ignore.append(
            'openre/device/%s/' % module_name
        )
        collect_ignore.append(
            'openre/device/%s.py' % module_name
        )
        continue

