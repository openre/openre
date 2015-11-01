# -*- coding: utf-8 -*-
"""
События. Экземпляр класса EventPool будет содержать все активные события (Event)
до их выполнения.
"""
from openre.agent.helpers import do_strict_action
import time
import traceback as _traceback
import logging

class EventPool(object):
    def __init__(self):
        self.event_list = []
        self.context = {}

    def register(self, event):
        if event.is_done:
            return
        self.event_list.append(event)
        self.event_list.sort(key=lambda x: -x.priority)
        event.set_pool(self)

    def poll_timeout(self):
        """
        returns value in milliseconds
        If all events in pull with timeout, than return minimum period till
            expire
        else if events - return 0
        else - return -1
        """
        timeout = None
        for event in self.event_list:
            event_timeout = event.wait_seconds()
            if event_timeout == 0:
                return 0
            if timeout is None or timeout > event_timeout:
                timeout = event_timeout
        if timeout is None:
            return -1
        return int(1000*timeout)

    def tick(self):
        lst = self.event_list
        for event in lst:
            if not event.is_done:
                event.run()
            if event.is_done:
                self.event_list.remove(event)


class Event(object):
    def __init__(self, action, namespace='default', message=None, bytes=None):
        self.message = message
        self.is_done = False
        self.is_prevent_done = False
        self.timeout_start = None
        self.timeout_value = None
        self.expire_start = None
        self.expire_value = None
        self.pool = None
        self.result = None
        self.error = None
        self.error_class = None
        self.traceback = None
        self.is_success = None
        self._done_callback = None
        self.action = action
        self.namespace = namespace
        self.context = {}
        self.is_first_run = True
        self._priority = 0
        if bytes is None:
            bytes = []
        if not isinstance(bytes, list):
            bytes = [bytes]
        self.bytes = bytes

    @property
    def priority(self):
        return self._priority

    def set_priority(self, priority=0):
        assert not self.pool
        self._priority = int(priority or 0)

    @property
    def inc_priority(self):
        assert not self.pool
        self._priority += 1

    @property
    def dec_priority(self):
        assert not self.pool
        self._priority -= 1

    def failed(self, error, traceback=False):
        self.is_success = False
        self.error = str(error)
        logging.warn('Task failed with error: %s', self.error)
        if traceback:
            self.traceback = _traceback.format_exc()
            logging.warn(self.traceback)
        else:
            self.traceback = self.error
        self.done()

    def set_pool(self, pool):
        self.pool = pool

    def wait_seconds(self):
        if not self.timeout_start:
            return 0
        ret = self.timeout_value - (time.time() - self.timeout_start)
        if ret < 0:
            return 0
        return ret

    def timeout(self, sec):
        self.prevent_done()
        self.timeout_start = time.time()
        self.timeout_value = sec

    def expire(self, sec):
        self.expire_start = time.time()
        self.expire_value = sec

    def prevent_done(self):
        self.is_prevent_done = True

    def done(self):
        if self.is_done:
            return
        self.is_done = True
        if self.is_success is None:
            self.is_success = True
        if self._done_callback:
            self._done_callback(self)

    def done_callback(self, callback):
        self._done_callback = callback

    def run(self):
        if self.expire_value \
           and time.time() - self.expire_start >= self.expire_value:
            self.failed('Event(%s) expired' % repr(self.action),
                        traceback=False)
            return
        if self.timeout_value \
           and time.time() - self.timeout_start < self.timeout_value:
            return
        if self.is_done:
            return
        if self.timeout_value:
            self.timeout_start = None
            self.timeout_value = None
        self.is_prevent_done = False
        try:
            args = {'args':[], 'kwargs': {}}
            if 'args' in self.message:
                args = self.message['args']
            self.result = do_strict_action(
                self.action, self.namespace, self, *args['args'],
                **args['kwargs'])
            self.is_first_run = False
        except Exception as error:
            self.failed(error, traceback=True)
        if self.message.get('no_reply'):
            self.done()
        elif self.is_prevent_done and not self.is_done:
            self.is_prevent_done = False
        elif not self.is_done:
            self.done()
    @property
    def data(self):
        return self.message

class AddressEvent(Event):
    def __init__(self, action, namespace='default', message=None, bytes=None,
                 address=None):
        self.address = address
        super(AddressEvent, self).__init__(action, namespace, message, bytes)

class DomainEvent(AddressEvent):
    pass

class ServerEvent(AddressEvent):
    @property
    def id(self):
        return self.message.get('id')

    @property
    def data(self):
        return self.message.get('data')


def test_event():
    pool = EventPool()
    event = ServerEvent(
        'process_state',
        message={
            'action': 'process_state',
            'id': 'uuid_id',
            'data': {}
        },
        address='socket_address'
    )
    assert pool.poll_timeout() == -1
    assert event.message['action'] == 'process_state'
    assert id(event.message['data']) == id(event.data)
    pool.register(event)
    assert pool.poll_timeout() == 0
    assert event.wait_seconds() == 0
    event.timeout(0.5)
    event.expire(0.1)
    assert pool.poll_timeout() > 300 and pool.poll_timeout() <= 500
    assert event.wait_seconds() > 0 and event.wait_seconds() <= 0.5
    time.sleep(0.11)
    pool.tick()
    assert not pool.event_list
    assert event.is_success is False
    assert event.error == "Event('process_state') expired"

    # priority
    ev0 = Event('priority0')
    assert ev0.priority == 0
    evm1 = Event('priority-1')
    evm1.set_priority(-1)
    assert evm1.priority == -1
    ev1 = Event('priority1')
    ev1.inc_priority
    assert ev1.priority == 1
    pool.register(ev0)
    pool.register(evm1)
    pool.register(ev1)
    assert pool.event_list == [ev1, ev0, evm1]
