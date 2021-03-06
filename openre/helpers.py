# -*- coding: utf-8 -*-
"""
Helper functions and decorators
"""
import cProfile
from functools import wraps
from copy import deepcopy
import os
import importlib
import inspect
import logging
import sys
import time
from random import randint
import json
import datetime
import re
import random
from openre.parse_func import explain
import uuid
from functools import partial

def randshift(start, end):
    """
    Returns number between:
        -end.....-start and start.....end
    """
    return (randint(0, 1) and -1 or 1) * randint(start, end)

CAN_SERIALIZE_FUNCTIONS = [
    max, min, random.randint, randshift
]
NAME_TO_FUNCTION = {}
for func in CAN_SERIALIZE_FUNCTIONS:
    NAME_TO_FUNCTION[func.__name__] = func

CAN_SERIALIZE_FUNCTIONS = NAME_TO_FUNCTION.values()



def profileit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        prof = cProfile.Profile()
        retval = prof.runcall(func, *args, **kwargs)
        import pstats
        pstats.Stats(prof).sort_stats('cumulative').print_stats(40)
        return retval
    return wrapper

# Backport of OrderedDict() class that runs on Python 2.4, 2.5, 2.6, 2.7 and pypy.
# Passes Python2.7's test suite and incorporates all the latest updates.
try:
    from thread import get_ident as _get_ident
except ImportError:
    from dummy_thread import get_ident as _get_ident

try:
    from _abcoll import KeysView, ValuesView, ItemsView
except ImportError:
    pass
import numpy as np

class OrderedDict(dict):
    'Dictionary that remembers insertion order'
    # An inherited dict maps keys to values.
    # The inherited dict provides __getitem__, __len__, __contains__, and get.
    # The remaining methods are order-aware.
    # Big-O running times for all methods are the same as for regular dictionaries.

    # The internal self.__map dictionary maps keys to links in a doubly linked list.
    # The circular doubly linked list starts and ends with a sentinel element.
    # The sentinel element never gets deleted (this simplifies the algorithm).
    # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

    def __init__(self, *args, **kwds):
        '''Initialize an ordered dictionary.  Signature is the same as for
        regular dictionaries, but keyword arguments are not recommended
        because their insertion order is arbitrary.

        '''
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__root
        except AttributeError:
            self.__root = root = []                     # sentinel node
            root[:] = [root, root, None]
            self.__map = {}
        self.__update(*args, **kwds)

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        'od.__setitem__(i, y) <==> od[i]=y'
        # Setting a new item creates a new link which goes at the end of the linked
        # list, and the inherited dictionary is updated with the new key/value pair.
        if key not in self:
            root = self.__root
            last = root[0]
            last[1] = root[0] = self.__map[key] = [last, root, key]
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        'od.__delitem__(y) <==> del od[y]'
        # Deleting an existing item uses self.__map to find the link which is
        # then removed by updating the links in the predecessor and successor nodes.
        dict_delitem(self, key)
        link_prev, link_next, key = self.__map.pop(key)
        link_prev[1] = link_next
        link_next[0] = link_prev

    def __iter__(self):
        'od.__iter__() <==> iter(od)'
        root = self.__root
        curr = root[1]
        while curr is not root:
            yield curr[2]
            curr = curr[1]

    def __reversed__(self):
        'od.__reversed__() <==> reversed(od)'
        root = self.__root
        curr = root[0]
        while curr is not root:
            yield curr[2]
            curr = curr[0]

    def clear(self):
        'od.clear() -> None.  Remove all items from od.'
        try:
            for node in self.__map.itervalues():
                del node[:]
            root = self.__root
            root[:] = [root, root, None]
            self.__map.clear()
        except AttributeError:
            pass
        dict.clear(self)

    def popitem(self, last=True):
        '''od.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned in LIFO order if last is true or FIFO order if false.

        '''
        if not self:
            raise KeyError('dictionary is empty')
        root = self.__root
        if last:
            link = root[0]
            link_prev = link[0]
            link_prev[1] = root
            root[0] = link_prev
        else:
            link = root[1]
            link_next = link[1]
            root[1] = link_next
            link_next[0] = root
        key = link[2]
        del self.__map[key]
        value = dict.pop(self, key)
        return key, value

    # -- the following methods do not depend on the internal structure --

    def keys(self):
        'od.keys() -> list of keys in od'
        return list(self)

    def values(self):
        'od.values() -> list of values in od'
        return [self[key] for key in self]

    def items(self):
        'od.items() -> list of (key, value) pairs in od'
        return [(key, self[key]) for key in self]

    def iterkeys(self):
        'od.iterkeys() -> an iterator over the keys in od'
        return iter(self)

    def itervalues(self):
        'od.itervalues -> an iterator over the values in od'
        for k in self:
            yield self[k]

    def iteritems(self):
        'od.iteritems -> an iterator over the (key, value) items in od'
        for k in self:
            yield (k, self[k])

    def update(*args, **kwds):
        '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.

        If E is a dict instance, does:           for k in E: od[k] = E[k]
        If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
        Or if E is an iterable of items, does:   for k, v in E: od[k] = v
        In either case, this is followed by:     for k, v in F.items(): od[k] = v

        '''
        if len(args) > 2:
            raise TypeError('update() takes at most 2 positional '
                            'arguments (%d given)' % (len(args),))
        elif not args:
            raise TypeError('update() takes at least 1 argument (0 given)')
        self = args[0]
        # Make progressively weaker assumptions about "other"
        other = ()
        if len(args) == 2:
            other = args[1]
        if isinstance(other, dict):
            for key in other:
                self[key] = other[key]
        elif hasattr(other, 'keys'):
            for key in other.keys():
                self[key] = other[key]
        else:
            for key, value in other:
                self[key] = value
        for key, value in kwds.items():
            self[key] = value

    __update = update  # let subclasses override update without breaking __init__

    __marker = object()

    def pop(self, key, default=__marker):
        '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
        If key is not found, d is returned if given, otherwise KeyError is raised.

        '''
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self.__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
        if key in self:
            return self[key]
        self[key] = default
        return default

    def __repr__(self, _repr_running={}):
        'od.__repr__() <==> repr(od)'
        call_key = id(self), _get_ident()
        if call_key in _repr_running:
            return '...'
        _repr_running[call_key] = 1
        try:
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())
        finally:
            del _repr_running[call_key]

    def __reduce__(self):
        'Return state information for pickling'
        items = [[k, self[k]] for k in self]
        inst_dict = vars(self).copy()
        for k in vars(OrderedDict()):
            inst_dict.pop(k, None)
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def copy(self):
        'od.copy() -> a shallow copy of od'
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
        and values equal to v (which defaults to None).

        '''
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        '''
        if isinstance(other, OrderedDict):
            return len(self)==len(other) and self.items() == other.items()
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

    # -- the following methods are only used in Python 2.7 --

    def viewkeys(self):
        "od.viewkeys() -> a set-like object providing a view on od's keys"
        return KeysView(self)

    def viewvalues(self):
        "od.viewvalues() -> an object providing a view on od's values"
        return ValuesView(self)

    def viewitems(self):
        "od.viewitems() -> a set-like object providing a view on od's items"
        return ItemsView(self)


class StatsMixin(object):
    """
    Различная статистика работы объекта
    """
    def __init__(self, *args, **kwargs):
        self._stats = {}
        super(StatsMixin, self).__init__(*args, **kwargs)

    def _get_stats(self, name, default=None):
        """
        expand name like ['spikes_sent_to', 'D1'] to
        self._stats['spikes_sent_to']['D1'].
        If it does not exists - init it with default value.
        """
        if isinstance(name, basestring):
            return self._stats.get(name, default)
        stats = self._stats
        length = len(name)
        key = name[0]
        for pos, key in enumerate(name):
            is_last = pos == (length - 1)
            if key not in stats:
                return default
            if is_last:
                return stats[key]
            stats = stats[key]
        return default

    def _set_stats(self, name, value):
        """
        expand name like ['spikes_sent_to', 'D1'] to
        self._stats['spikes_sent_to']['D1'].
        If it does not exists - init it with default value.
        """
        if isinstance(name, basestring):
            name = [name]
        stats = self._stats
        length = len(name)
        for pos, key in enumerate(name):
            is_last = pos == (length - 1)
            if key not in stats:
                if not is_last:
                    stats[key] = {}
            if is_last:
                stats[key] = value
            stats = stats[key]
        return value

    def stat_inc(self, name, value=1):
        """
        Увеличивает значение name на value
        """
        self._set_stats(name, self._get_stats(name, 0) + value)

    def stat_dec(self, name, value=1):
        """
        Уменьшает значение name на value
        """
        self._set_stats(name, self._get_stats(name, 0) - value)

    def stat_set(self, name, value):
        """
        Устанавливает значение name равным value
        """
        if isinstance(value, np.number):
            value = value.item()
        self._set_stats(name, value)

    def stat(self, name=None):
        """
        Получает значение name
        """
        if name is None:
            return deepcopy(self._stats)
        return self._get_stats(name)

def merge(source, destination):
    """
    Deep merge source dictionary to destination
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge(value, node)
        else:
            destination[key] = value

    return destination

def set_default(source, defaults):
    """
    Recursively updates source from data if no source
    """
    for key, value in defaults.items():
        if isinstance(value, dict):
            if key not in source:
                source[key] = {}
            set_default(source[key], value)
        elif isinstance(value, list) and len(value) == 1 \
                and isinstance(value[0], dict):
            if key in source and isinstance(source[key], list):
                for row in source[key]:
                    set_default(row, value[0])
        elif key not in source:
            source[key] = deepcopy(value)

    return defaults


def test_helpers():
    defaults = {'first': {'all_rows': {'pass': 'dog', 'number': '1'}}}
    data = {'first': {'all_rows': {'fail': 'cat', 'number': '5'}}}
    assert merge(data, defaults) == {'first': {'all_rows': \
            {'pass': 'dog', 'fail': 'cat', 'number': '5'}}}
    defaults = {'first': {'all_rows': {'pass': 'dog', 'number': '1'}},
                'second' :[1, 2], 'none':{1:2}}
    data = {'first': {'all_rows': {'fail': 'cat', 'number': '5'}},
            'second': '3'}
    before_id = id(data)
    def_before_id = id(defaults)
    set_default(data, defaults)
    assert id(data) == before_id
    assert id(defaults) == def_before_id
    assert data == {
        'first': {'all_rows': {'pass': 'dog', 'fail': 'cat', 'number': '5'}},
        'second': '3',
        'none': {1:2}
    }
    # check not changed
    assert defaults == {'first': {'all_rows': {'pass': 'dog', 'number': '1'}},
                'second' :[1, 2], 'none':{1:2}}
    data = {
        'connect': [
            {'name': 'V2', 'shift': [1, 2]},
            {'name': 'V3', 'radius': 2},
        ]
    }
    defaults = {
        'connect': [{
            'radius': 1,
            'shift': [0, 0],
        }]
    }
    set_default(data, defaults)
    assert data == {
        'connect': [{'shift': [1, 2], 'radius': 1, 'name': 'V2'},
                    {'shift': [0, 0], 'radius': 2, 'name': 'V3'}]
    }

class Devices(object):
    """
    Device modules import statuses.
    """
    def __init__(self):
        self.messages = []
        self.devices = {}

    def import_success(self, module_name, devices=None):
        if devices is None:
            devices = []
        if module_name in self.devices:
            return
        self.devices[module_name] = 1
        self.messages.append({
            'module': module_name,
            'status': True,
            'message': '',
            'devices': list(devices),
        })

    def import_error(self, module_name, error_help_text):
        if module_name in self.devices:
            return
        self.devices[module_name] = 1
        self.messages.append({
            'module': module_name,
            'status': False,
            'message': error_help_text,
            'devices': [],
        })

    def __str__(self):
        res = []
        for row in self.messages:
            res.append(
                '%s: %s %s' % (row['module'],
                               row['status'] and 'OK' or 'FAIL',
                               row['devices']))
            if row['message']:
                res.append(row['message'])
        return '\n'.join(res)

DEVICES = Devices()

def try_import_devices(file_name, target_module_name, error_help_text):
    current_module = sys.modules[target_module_name]
    from openre.device.abstract import Device
    from openre.device.iobase import IOBase
    base_dir = os.path.dirname(file_name)
    device_group_name = os.path.basename(base_dir)
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
            module = importlib.import_module(
                'openre.device.%s.%s' % (device_group_name, module_name)
            )
        except ImportError as err:
            logging.debug(
                'Module %s not imported, so devices from this module will ' \
                'not be available. Error: %s',
                'openre.device.%s' % module_name,
                str(err)
            )
            DEVICES.import_error(
                'openre.device.%s.%s' % (device_group_name, module_name),
                '\n'.join([str(err), error_help_text])
            )
            continue
        devices = []
        for attr_name in dir(module):
            if attr_name[0:2] == '__' or attr_name in ['Device']:
                continue
            attr = getattr(module, attr_name)
            if not inspect.isclass(attr):
                continue
            if issubclass(attr, Device) and not attr in [IOBase]:
                setattr(current_module, attr_name, attr)
                devices.append(attr_name)

        DEVICES.import_success(
            'openre.device.%s.%s' % (device_group_name, module_name), devices)

# https://gist.github.com/gregburek/1441055
def rate_limited(max_per_second):
    """
    Decorator that make functions not be called faster than
    """
    min_interval = 1.0 / float(max_per_second)

    def decorate(func):
        last_time_called = [0.0]

        @wraps(func)
        def rate_limited_function(*args, **kwargs):
            elapsed = time.time() - last_time_called[0]
            left_to_wait = min_interval - elapsed

            if left_to_wait > 0:
                time.sleep(left_to_wait)

            ret = func(*args, **kwargs)
            last_time_called[0] = time.time()
            return ret

        return rate_limited_function

    return decorate


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

def test_randshift():
    assert randshift(5, 5) in [-5, 5]

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
