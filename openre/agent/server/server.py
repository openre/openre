# -*- coding: utf-8 -*-
"""
Основной код сервера
"""
import logging
import zmq

def run(args):
    context = zmq.Context()
    socket = context.socket(zmq.ROUTER)
    try:
        socket.bind("tcp://%s:%s" % (args.host, args.port))
    except zmq.error.ZMQError as error:
        if error.errno == 98: # Address already in use
            logging.warn(
                "Address tcp://%s:%s already in use. Server is already " \
                "runnning?",
                args.host, args.port)
        raise
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    while True:
        socks = dict(poller.poll())
        if socks.get(socket) == zmq.POLLIN:
            message = socket.recv_multipart()
            logging.debug('Received message: %s', message)
            socket.send_multipart([message[0], '', b"World"])

def clean():
    logging.debug('Cleaning')
