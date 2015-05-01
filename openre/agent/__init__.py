# -*- coding: utf-8 -*-
"""
OpenRE.Agent - агент для запуска доменов.
"""
from openre.agent.args import parser
import logging

def run():
    args, unknown = parser.parse_known_args()
    mod = None
    if args.type == 'server':
        from openre.agent import server as mod
    if mod:
        mod.run()
    else:
        logging.error('Module not found')

