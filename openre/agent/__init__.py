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

