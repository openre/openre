# -*- coding: utf-8 -*-
import logging
import signal
from lockfile.pidlockfile import PIDLockFile
import os
import time
import zmq
import uuid
import json
import datetime
import re
from types import FunctionType
import traceback

ZMQ = {'context':None}
def get_zmq_context():
    """
    Создает один глобальный контекст для zmq.
    Если контекст уже создан, то возвращает ранее созданный.
    """
    if not ZMQ['context']:
        ZMQ['context'] = zmq.Context()
    return ZMQ['context']


def term_zmq_context():
    """
    Удаляет глобальный контекст.
    """
    if not ZMQ['context']:
        return
    ZMQ['context'].term()
    ZMQ['context'] = None

def daemon_stop(pid_file=None):
    """
    If pid is provided - then run try to stop daemon.
    Else - just return.
    """
    logging.debug('Stop daemon')
    if not pid_file:
        logging.debug('No pid file provided - nothing to stop')
        return
    pid_path = os.path.abspath(pid_file)
    pidfile = PIDLockFile(pid_path, timeout=-1)
    try:
        pid_num = pidfile.read_pid()
        os.kill(pid_num, signal.SIGTERM)
        # number of tries to check (every 1 sec) if agent is stoped
        tries = 600
        success = False
        while tries:
            tries -= 1
            time.sleep(1)
            try:
                os.kill(pid_num, 0)
            except OSError:  #No process with locked PID
                success = True
                break
        if success:
            logging.debug('Daemon successfully stopped')
        else:
            logging.warn('Unable to stop daemon')

    except TypeError: # no pid file
        logging.debug('Pid file not found')
    except OSError:
        logging.debug('Process not running')

class OREEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return 'ISODate("%s")' % date_to_str(obj)
        elif isinstance(obj, datetime.time):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return 'UUID("%s")' % str(obj)
        return json.JSONEncoder.default(self, obj)


class OREDecoder(json.JSONDecoder):
    datetime_regex = re.compile(
        r'ISODate\(\"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})' \
        r'(?:\.(\d+))?Z\"\)'
    )
    uuid_regex = re.compile(
        r'UUID\(\"([a-f0-9]{8}\-[a-f0-9]{4}\-[a-f0-9]{4}' \
        r'\-[a-f0-9]{4}\-[a-f0-9]{12})\"\)'
    )

    def decode(self, obj):
        ret = super(OREDecoder, self).decode(obj)
        ret = self.parse_result(ret)
        return ret

    def parse_result(self, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = self.parse_result(v)
        elif isinstance(obj, list):
            for k, v in enumerate(obj):
                obj[k] = self.parse_result(v)
        elif isinstance(obj, basestring):
            obj = self._hook(obj)
        return obj

    def _hook(self, obj):
        dt_result = OREDecoder.datetime_regex.match(obj)
        if dt_result:
            year, month, day, hour, minute, second, milliseconds \
                    = map(lambda x: int(x or 0), dt_result.groups())
            return datetime.datetime(year, month, day, hour, minute, second,
                                     milliseconds)

        uuid_result = OREDecoder.uuid_regex.match(obj)
        if uuid_result:
            return uuid.UUID(uuid_result.group(1))
        return obj


def to_json(data, sort_keys=False):
    return json.dumps(data, sort_keys=sort_keys, cls=OREEncoder)

def from_json(data):
    return json.loads(data, cls=OREDecoder)

def date_to_str(date):
    """ Converts a datetime value to the corresponding RFC-1123 string."""
    if date and date.year == 1 and date.month == 1 and date.day == 1:
        date = None
    if not date:
        return None
    ret = None
    try:
        ret = datetime.datetime.strftime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        ret = date.isoformat()
        try:
            ret.index('T')
        except ValueError:
            ret += 'T00:00:00.000000Z'
        try:
            ret.index('.')
        except ValueError:
            ret += '.000000Z'
        try:
            ret.index('Z')
        except ValueError:
            ret += 'Z'
    return ret

def priority_func(row):
    if type(row['priority']) == FunctionType:
        return row['priority']()
    return row['priority']

class Hooks(object):
    _callbacks = None
    _was = None

    @classmethod
    def add_action(cls, action, callback, priority):
        if action not in cls._was:
            cls._was[action] = []
        if action not in cls._callbacks:
            cls._callbacks[action] = []
        if callback not in cls._was[action]:
            row = {
                'callback': callback,
                'priority': priority,
            }
            cls._callbacks[action].append(row)
            cls._was[action].append(row)

    @classmethod
    def registered_action(cls, action):
        return action in cls._callbacks

    @classmethod
    def do_action(cls, action, *args, **kwargs):
        rows = cls._callbacks.get(action, [])
        rows = sorted(rows, key=priority_func)
        ret = None
        for row in rows:
            ret = row['callback'](*args, **kwargs)
        return ret

class ActionHooks(Hooks):
    _callbacks = {}
    _was = {}

class FilterHooks(Hooks):
    _callbacks = {}
    _was = {}

    @classmethod
    def do_action(cls, action, value):
        rows = cls._callbacks.get(action, [])
        rows = sorted(rows, key = priority_func)
        for row in rows:
            value = row['callback'](value)
        return value

def add_action(action, callback, priority=50):
    ActionHooks.add_action(action, callback, priority)

def do_action(action, *args, **kwargs):
    return ActionHooks.do_action(action, *args, **kwargs)

def do_strict_action(action, *args, **kwargs):
    if not ActionHooks.registered_action(action):
        raise ValueError('Action "%s" in not registered' % action)
    return ActionHooks.do_action(action, *args, **kwargs)

def add_filter(action, callback, priority=50):
    FilterHooks.add_action(action, callback, priority)

def do_filter(action, value):
    return FilterHooks.do_action(action, value)

class Transport(object):
    def __init__(self, *args, **kwargs):
        super(Transport, self).__init__()
        self.context = get_zmq_context()
        self._connection_pool = []

    def clean_sockets(self):
        for socket in self._connection_pool:
            self.disconnect(socket)

    def socket(self, *args, **kwargs):
        socket = self.context.socket(*args, **kwargs)
        # The value of 0 specifies no linger period. Pending messages shall be
        # discarded immediately when the socket is closed with zmq_close().
        socket.setsockopt(zmq.LINGER, 0)
        return socket

    def disconnect(self, socket):
        if socket in self._connection_pool:
            logging.debug('agent.disconnect(%s)', socket)
            self._connection_pool.remove(socket)
            socket.close()
            socket = None
            return True
        return False

    def connect(self, host, port):
        logging.debug('agent.connect(%s, %s)', repr(host), repr(port))
        socket = self.socket(zmq.REQ)
        self._connection_pool.append(socket)
        socket.connect('tcp://%s:%s' % (
            host == '*' and '127.0.0.1' or host,
            port
        ))
        return socket

    def to_json(self, data):
        try:
            data = to_json(data)
        except ValueError:
            logging.warn('Cant convert to json: %s', data)
            raise
        return data

    def from_json(self, json):
        try:
            json = from_json(json)
        except ValueError:
            logging.warn('Message is not valid json: %s', json)
        return json


class AgentBase(Transport):
    """
    Абстрактный класс агента.
    """
    # if set to True - than init socket that connects to server.
    # should be set self.config.server_host and self.config.server_port
    server_connect = False
    # connect to broker as a worker (so this agent is local and can reply to
    # requests)
    broker_connect = False
    def __init__(self, config):
        self.config = config
        self.id = config.id or uuid.uuid4()
        self.__run_user = self.run
        self.run = self.__run
        self.__clean_user = self.clean
        self.clean = self.__clean
        self.server_socket = None
        self.server = None
        super(AgentBase, self).__init__()
        if self.__class__.server_connect:
            self.connect_server(
                self.config.server_host,
                self.config.server_port
            )
        if self.__class__.server_connect:
            self.send_server('process_state', {
                'status': 'init',
                'pid': os.getpid(),
                'name': self.config.type,
            })
        if 'log_level' in self.config and self.config.log_level:
            logging.basicConfig(
                format='%(levelname)s:%(message)s',
                level=getattr(logging, self.config.log_level)
            )


        try:
            self.init()
        except Exception:
            if self.__class__.server_connect:
                self.send_server('process_state', {
                    'status': 'error',
                    'pid': 0,
                    'message': traceback.format_exc()
                })
            raise

    def init(self):
        """
        Весь код инициализации здесь. Если очень нужно переопределить __init__,
        то обязательно использовать
        super(Agent, self).__init__(*args, **kwargs)
        в начале переопределенного метода
        """
        pass

    def run(self):
        """
        Код запуска агента. Этот метод необходимо переопределить.
        """
        raise NotImplementedError

    def clean(self):
        """
        Очистка при завершении работы агента. Этот метод можно переопределить.
        """

    def __run(self):
        try:
            if self.__class__.server_connect:
                self.send_server('process_state', {
                    'status': 'run'
                })

            self.__run_user()
        except Exception:
            raise
        finally:
            self.clean()

    def __clean(self):
        logging.debug('Agent cleaning')
        if self.__class__.server_connect:
            self.send_server('process_state', {
                'status': 'clean',
            })
        self.__clean_user()
        if self.__class__.server_connect:
            self.send_server('process_state', {
                'status': 'exit',
                'pid': 0,
            })
        self.clean_sockets()
        if self.server_socket:
            self.server_socket = None

    def connect_server(self, host, port):
        self.server_socket = self.connect(host, port)
        self.server = RPC(self.server_socket)

    def send_server(self, action, data=None, skip_recv=False):
        message = {
            'action': action,
            'id': self.id,
            'data': data
        }
        message = self.to_json(message)
        logging.debug('Agent->Server: %s', message)
        self.server_socket.send(message)
        ret = None
        if not skip_recv:
            ret = self.server_socket.recv()
            ret = self.from_json(ret)
            logging.debug('Server->Agent: %s', ret)
        return ret

class RPCException(Exception):
    def __init__(self, result, *args, **kwargs):
        self.result = result
        super(RPCException, self).__init__(*args, **kwargs)

class RPC(object):
    """
    Удаленное выполнение процедур
    """
    def __init__(self, socket):
        self._socket = socket
        self._response = None

    def __getattr__(self, name):
        if hasattr(self, name):
            return super(RPC, self).__getattr__(name)
        def api_call(*args, **kwargs):
            self._response = None
            message = {
                'action': name,
                'data': {},
                'args': {
                    'args': args,
                    'kwargs': kwargs
                }
            }
            message = to_json(message)
            logging.debug('RPC call server.%s(*%s, **%s)', name, args, kwargs)
            self._socket.send(message)
            ret = self._socket.recv()
            ret = from_json(ret)
            self._response = ret
            logging.debug('RPC result %s', ret)
            if not ret['success']:
                if 'traceback' in ret and ret['traceback']:
                    raise RPCException(ret, ret['traceback'])
                raise RPCException(ret, ret['error'])
            return ret['data']

        return api_call

class RPCProxy(object):
    """
    Удаленное выполнение процедур с помощью промежуточного прокси
    """
    def __init__(self, socket, proxy_method, *args, **kwargs):
        self._socket = socket
        self._response = None
        self._proxy_method = proxy_method
        self._proxy_args = args
        self._proxy_kwargs = kwargs

    def __getattr__(self, name):
        if hasattr(self, name):
            return super(RPCProxy, self).__getattr__(name)
        def api_call(*args, **kwargs):
            self._response = None
            # original message
            message = {
                'action': name,
                'data': {},
                'args': {
                    'args': args,
                    'kwargs': kwargs
                }
            }
            # pack message to envelope
            message = {
                'action': self._proxy_method,
                'data': message,
                'args': {
                    'args': self._proxy_args,
                    'kwargs': self._proxy_kwargs
                }
            }
            message = to_json(message)
            logging.debug('RPC Proxy call %s.%s(*%s, **%s)',
                          self._proxy_method, name, args, kwargs)
            self._socket.send(message)
            ret = self._socket.recv()
            ret = from_json(ret)
            self._response = ret
            logging.debug('RPC Proxy result %s', ret)
            if not ret['success']:
                if 'traceback' in ret and ret['traceback']:
                    raise RPCException(ret, ret['traceback'])
                raise RPCException(ret, ret['error'])
            return ret['data']

        return api_call
