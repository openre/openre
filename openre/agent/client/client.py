# -*- coding: utf-8 -*-
"""
Основной код сервера
"""
import zmq
import logging

def hello(args):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://%s:%s" % (args.host, args.port))
    message = b'Hello'
    logging.debug("Send message: %s", message)
    socket.send(message)
    message = socket.recv()
    logging.debug("Received reply: %s", message)
