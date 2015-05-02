# -*- coding: utf-8 -*-
"""
Основной код прокси
"""
import logging
import zmq
import tempfile
import os

def run(args):

    context = zmq.Context()
    # Socket facing clients
    frontend = context.socket(zmq.SUB)
    try:
        frontend.bind("tcp://%s:%s" % (args.host, args.port))
    except zmq.error.ZMQError as error:
        if error.errno == 98: # Address already in use
            logging.warn(
                "Address tcp://%s:%s already in use. Proxy is already " \
                "runnning?",
                args.host, args.port)
        raise

    frontend.setsockopt(zmq.SUBSCRIBE, "")

    # Socket facing services
    ipc_file = os.path.join(tempfile.gettempdir(), 'openre-proxy')
    backend = context.socket(zmq.PUB)
    backend.bind("ipc://%s" % ipc_file)

    try:
        zmq.device(zmq.FORWARDER, frontend, backend)
    except Exception:
        raise
    finally:
        frontend.close()
        backend.close()
        context.term()

def clean():
    logging.debug('Cleaning')
