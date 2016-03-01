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
from parse_func import explain
from functools import partial
import random

ZMQ = {'context':None}
CAN_SERIALIZE_FUNCTIONS = [
    min, random.randint
]
NAME_TO_FUNCTION = {}
for func in CAN_SERIALIZE_FUNCTIONS:
    NAME_TO_FUNCTION[func.__name__] = func

CAN_SERIALIZE_FUNCTIONS = NAME_TO_FUNCTION.values()

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
        elif callable(obj) and obj in CAN_SERIALIZE_FUNCTIONS:
            return '@%s()' % str(obj.__name__)
        elif isinstance(obj, partial) and obj.func in CAN_SERIALIZE_FUNCTIONS:
            # no arguments
            if obj.args is None and obj.keywords is None:
                return '@%s()' % (obj.func.__name__, )
            args = obj.args
            kwargs = obj.keywords
            # args
            if args:
                if not isinstance(args, (list, tuple)):
                    args = [args]
                args = ', '.join([to_json(x) for x in args])
            # args and kwargs
            if kwargs:
                kwargs = ['%s=%s' % (key, to_json(value))
                          for key, value in kwargs.items()]
                kwargs = ', '.join(kwargs)
            if all([args, kwargs]):
                return '@%s(%s, %s)' % (obj.func.__name__, args, kwargs)
            elif any([args, kwargs]):
                return '@%s(%s)' % (obj.func.__name__, args or kwargs)
            else:
                return '@%s()' % str(obj.func.__name__)
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
        # restore function
        if obj and obj[0] == '@':
            try:
                exp = explain(obj[1:])
                if exp:
                    exp = exp[0]
                func = NAME_TO_FUNCTION[exp.func]
                args = exp.args or []
                kwargs = exp.keywords or {}
                #args = [from_json(x) for x in args]
                kwargs = dict([
                    (key, value) for key, value in kwargs.items()
                ])
                return partial(func, *args, **kwargs)
            except (SyntaxError, TypeError, KeyError):
                pass
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
    def add_action(cls, action, callback, priority, namespace='default'):
        if namespace not in cls._was:
            cls._was[namespace] = {}
        if namespace not in cls._callbacks:
            cls._callbacks[namespace] = {}
        if action not in cls._was[namespace]:
            cls._was[namespace][action] = []
        if action not in cls._callbacks[namespace]:
            cls._callbacks[namespace][action] = []
        if callback not in cls._was[namespace][action]:
            row = {
                'callback': callback,
                'priority': priority,
            }
            cls._callbacks[namespace][action].append(row)
            cls._was[namespace][action].append(row)

    @classmethod
    def registered_action(cls, action, namespace='default'):
        if namespace not in cls._callbacks:
            return False
        return action in cls._callbacks[namespace]

    @classmethod
    def do_action(cls, action, namespace, *args, **kwargs):
        rows = cls._callbacks.get(namespace, {}).get(action, [])
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
    def do_action(cls, action, value, namespace='default'):
        rows = cls._callbacks.get(namespace, {}).get(action, [])
        rows = sorted(rows, key=priority_func)
        for row in rows:
            value = row['callback'](value)
        return value

def add_action(action, callback, priority=50, namespace='default'):
    ActionHooks.add_action(action, callback, priority, namespace)

def do_action(action, namespace, *args, **kwargs):
    return ActionHooks.do_action(action, namespace, *args, **kwargs)

def is_registered_action(action, namespace):
    return ActionHooks.registered_action(action, namespace)

def do_strict_action(action, namespace, *args, **kwargs):
    if not is_registered_action(action, namespace):
        raise ValueError('Action "%s" in not registered' % action)
    return ActionHooks.do_action(action, namespace, *args, **kwargs)

def add_filter(action, callback, priority=50, namespace='default'):
    FilterHooks.add_action(action, callback, priority, namespace)

def do_filter(action, value, namespace='default'):
    return FilterHooks.do_action(action, value, namespace)

class Transport(object):
    def __init__(self, *args, **kwargs):
        super(Transport, self).__init__()
        self._context = get_zmq_context()
        self._connection_pool = []

    def clean_sockets(self):
        sockets = list(self._connection_pool)
        for socket in sockets:
            self.disconnect(socket)

    def socket(self, *args, **kwargs):
        socket = self._context.socket(*args, **kwargs)
        # The value of 0 specifies no linger period. Pending messages shall be
        # discarded immediately when the socket is closed with zmq_close().
        socket.setsockopt(zmq.LINGER, 0)
        return socket

    def disconnect(self, socket):
        if socket in self._connection_pool:
            logging.debug('agent.disconnect(%s)', repr(socket))
            self._connection_pool.remove(socket)
            socket.close()
            socket = None
            return True
        return False

    def connect(self, host, port):
        logging.debug('agent.connect(%s, %s)', repr(host), repr(port))
        socket = self.socket(zmq.DEALER)
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
        self.id = config.get('id') or uuid.uuid4()
        self.__run_user = self.run
        self.run = self.__run
        self.__clean_user = self.clean
        self.clean = self.__clean
        self.server_socket = None
        self.server = None
        super(AgentBase, self).__init__()
        if self.__class__.server_connect:
            self.connect_server(
                self.config['server_host'],
                self.config['server_port']
            )
        if self.__class__.server_connect:
            self.send_server('process_state', {
                'status': 'init',
                'pid': os.getpid(),
                'name': self.config['type'],
            })

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
            if self.__class__.server_connect:
                logger_level = logging.getLogger().getEffectiveLevel()
                if logger_level <= logging.DEBUG or True:
                    self.send_server('error', traceback.format_exc())
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
        self.server_socket.send_multipart(['', message])
        ret = None
        if not skip_recv:
            ret = self.server_socket.recv_multipart()
            assert ret[0] == ''
            ret = self.from_json(ret[1])
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
        super(RPC, self).__init__()

    def __getattr__(self, name):
        def api_call(*args, **kwargs):
            self._response = None
            message = {
                'action': name,
                'args': {
                    'args': args,
                    'kwargs': kwargs
                }
            }
            message = to_json(message)
            logging.debug('RPC >>> server.%s',
                          pretty_func_str(name, *args, **kwargs))
            self._socket.send_multipart(['', message])
            ret = self._socket.recv_multipart()
            assert ret[0] == ''
            ret = from_json(ret[1])
            self._response = ret
            logging.debug('RPC %s', ret)
            if not ret['success']:
                if 'traceback' in ret and ret['traceback']:
                    raise RPCException(ret, ret['traceback'])
                raise RPCException(ret, ret['error'])
            return ret['data']

        return api_call

class RPCBrokerProxyCall(object):
    """
    Возвращается как функция в RPCBrokerProxy, которой передадутся параметры
    для вызова удаленного метода. Нужна для того, что бы можно было задавать
    дополнительные параметры при вызове, например:
        >>> broker = RPCBrokerProxy(socket, proxy_method, broker_address)
        # вызов при котором не ждем результата выполнения функции.
        # Вернется event_id после регистрации события на сервере.
        >>> broker.some_remote_method(arguments)
        # тут дожидаемся результата выполнения удаленного метода.
        >>> broker.some_remote_method.wait(arguments)
        # вообще не ждем никакого ответа
        >>> broker.some_remote_method.no_reply(arguments)
    """
    def __init__(self, proxy, name):
        self.proxy = proxy
        self.name = name
        self._wait = False
        self._no_reply = False
        self._bytes = []
        self._priority = 0

    def __call__(self, *args, **kwargs):
        self._response = None
        # original message
        message = {
            'action': self.name,
            'wait': self._wait,
            'no_reply': self._no_reply,
            'bytes': len(self._bytes),
            'priority': int(self._priority),
            'args': {
                'args': args,
                'kwargs': kwargs
            }
        }
        # pack message to envelope
        message = {
            'action': self.proxy._proxy_method,
            'address': self.proxy._proxy_address,
            'data': message,
            'wait': self._wait,
            'no_reply': self._no_reply,
            'bytes': len(self._bytes),
            'priority': int(self._priority),
            'args': {
                'args': self.proxy._proxy_args,
                'kwargs': self.proxy._proxy_kwargs
            }
        }
        message = to_json(message)
        logging.debug('RPC broker proxy >>> %s',
                      pretty_func_str('%s.%s' % (
                          self.proxy._proxy_method, self.name),
                          *args, **kwargs)
                     )
        packet = ['', message]
        if self._bytes:
            packet.extend(self._bytes)
        self.proxy._socket.send_multipart(packet)
        ret = {'success': True, 'data': None}
        if not self._no_reply:
            ret = self.proxy._socket.recv_multipart()
            assert ret[0] == ''
            ret = from_json(ret[1])
        self.proxy._response = ret
        logging.debug('RPC broker proxy %s', ret)
        if not ret['success']:
            if 'traceback' in ret and ret['traceback']:
                raise RPCException(ret, ret['traceback'])
            raise RPCException(ret, ret['error'])
        return ret['data']

    @property
    def wait(self):
        """
        Указывает на то, что нужно подождать результата выполнения команды
        """
        self._wait = True
        return self

    def set_priority(self, priority=0):
        """
        Устанавливает приоритет команды
        """
        self._priority = priority
        return self

    @property
    def inc_priority(self):
        """
        Увеличивает приоритет команды
        """
        self._priority += 1
        return self

    @property
    def dec_priority(self):
        """
        Уменьшает приоритет команды
        """
        self._priority -= 1
        return self

    @property
    def no_reply(self):
        """
        Указывает на то, что ответ с результатом выполнения команды посылать
        не нужно
        """
        self._no_reply = True
        return self

    def set_bytes(self, value):
        """
        Указывает на то, что нужно переслать список из строк в бинарном виде
        """
        if value is None:
            return
        if not isinstance(value, list):
            value = [value]
        self._bytes = value
        return self

class RPCBrokerProxy(object):
    """
    Удаленное выполнение процедур на брокере с помощью промежуточного прокси на
    сервере. Используется в клиенте.
    """
    def __init__(self, socket, proxy_method, broker_address,
                 *args, **kwargs):
        self._socket = socket
        self._response = None
        self._proxy_method = proxy_method
        self._proxy_address = broker_address
        self._proxy_args = args
        self._proxy_kwargs = kwargs

    def __getattr__(self, name):
        # lazy socket
        if callable(self._socket):
            # actual connect
            self._socket = self._socket()
        return RPCBrokerProxyCall(self, name)

class RPCBroker(object):
    """
    Позволяет вызывать методы процессов, подключенных к брокеру в качестве
    воркеров.
    self.address - это id процесса, подключенного к брокеру.
    broker.set_address(address).run_remote_method(*args, **kwargs)
    """
    def __init__(self, socket):
        self._socket = socket
        self._response = None
        self._address = None
        self._response_address = None
        self._wait = False
        self._no_reply = False
        self._bytes = []
        self._priority = 0

    def set_address(self, address):
        """
        Sets address of a broker worker process
        """
        if isinstance(address, uuid.UUID):
            address = address.bytes
        self._address = bytes(address)
        return self

    def set_response_address(self, address):
        """
        Sets address of a server event id
        """
        self._response_address = address
        return self

    def set_wait(self, wait):
        """
        Sets flag if we need to wait the result
        """
        self._wait = wait
        return self

    def set_no_reply(self, no_reply):
        """
        Sets flag if we need to wait the result
        """
        self._no_reply = no_reply
        return self

    def set_bytes(self, value):
        """
        Указывает на то, что нужно переслать список из строк в бинарном виде
        """
        if value is None:
            return
        if not isinstance(value, list):
            value = [value]
        self._bytes = value
        return self

    def set_priority(self, priority=0):
        """
        Устанавливает приоритет команды
        """
        self._priority = priority
        return self

    @property
    def inc_priority(self):
        """
        Увеличивает приоритет команды
        """
        self._priority += 1
        return self

    @property
    def dec_priority(self):
        """
        Уменьшает приоритет команды
        """
        self._priority -= 1
        return self


    def __getattr__(self, name):
        def api_call(*args, **kwargs):
            assert self._address
            assert self._response_address
            # lazy socket
            if callable(self._socket):
                # actual connect
                self._socket = self._socket()
            self._response = None
            message = {
                'action': name,
                'wait': self._wait,
                'no_reply': self._no_reply,
                'bytes': len(self._bytes),
                'priority': int(self._priority),
                'context': {
                    'event_id': self._response_address,
                },
                'args': {
                    'args': args,
                    'kwargs': kwargs
                }
            }
            message = to_json(message)
            logging.debug('RPCBroker >>> broker.%s',
                          pretty_func_str(name, *args, **kwargs))
            packet = ['', self._address, message]
            if self._bytes:
                packet.extend(self._bytes)
            self._socket.send_multipart(packet)
            self._response_address = None
            self._bytes = None
            self._priority = 0

        return api_call

def pretty_func_str(__name, *args, **kwargs):
    """
    Возвращает строчку в виде: 'name(func_arguments)'
    """
    pretty_args = []
    if args:
        pretty_args.append(', '.join([repr(x) for x in args]))
    if kwargs:
        pretty_args.append(
            ', '.join(['%s=%s' % (k, repr(v))
                       for k, v in kwargs.items()])
        )
    pretty_args = ', '.join(pretty_args)
    return '%s(%s)' % (__name, pretty_args)


def test_json():
    dump = to_json({'shift': [
        partial(min, 0, 1, 2, test='kw argument test', num = 1)
    ]})
    assert dump == '{"shift": ["@min(0, 1, 2, test=\\"kw argument test\\", num=1)"]}'
    recover = from_json(dump)
    func = recover['shift'][0]
    assert isinstance(func, partial)
    assert func.func == min
    assert func.args == (0, 1, 2)
    assert func.keywords == {'test': 'kw argument test', 'num': 1}
    assert from_json('{"empty_string":""}') == {"empty_string":""}
