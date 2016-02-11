# content of conftest.py
import os
import importlib
import logging

collect_ignore = []

def get_modules(base_dir):
    ret = []
    device_group_name = os.path.basename(base_dir)
    if not os.path.isdir(base_dir):
        return []
    for module_file in sorted(
        [file_name for file_name in os.listdir(base_dir) \
         if ((os.path.isfile('%s/%s' % (base_dir, file_name)) \
              and file_name[-3:] == '.py'))
            and file_name not in ['__init__.py']]
    ):
        module_name = module_file.split('.')
        if module_name[-1] == 'py':
            del module_name[-1]
        module_name = '.'.join(module_name)
        try:
            importlib.import_module(
                'openre.device.%s.%s' % (device_group_name, module_name)
            )
        except ImportError:
            ret.append(
                'openre/device/%s/%s.py' % (device_group_name, module_name)
            )
    return ret

base_dir = os.path.join(os.path.dirname(__file__), 'openre/device')
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
    for row in get_modules(os.path.join(base_dir, module_file)):
        collect_ignore.append(row)

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


