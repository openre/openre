# -*- coding: utf-8 -*-
"""
События. Экземпляр класса EventPool будет содержать все активные события (Event)
до их выполнения.
"""
from openre.agent.helpers import do_strict_action
import time
import traceback as _traceback


class EventPool(object):
    def __init__(self):
        self.event_list = []

    def register(self, event):
        self.event_list.append(event)
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
            event.run()
            if event.is_done:
                self.event_list.remove(event)


class Event(object):
    def __init__(self, message, address):
        self.message = message
        self.address = address
        self.is_done = False
        self.is_prevent_done = False
        self.timeout_start = None
        self.timeout_value = None
        self.expire_start = None
        self.expire_value = None
        self.pool = None
        self.result = None
        self.error = None
        self.traceback = None
        self.is_success = None
        self._done_callback = None
        try:
            self.action = self.message['action']
            self.id = self.message['id']
        except ValueError as error:
            self.failed(error)

    def failed(self, error, traceback=True):
        self.is_done = True
        self.is_success = False
        self.error = str(error)
        if traceback:
            self.traceback = _traceback.format_exc()
        else:
            self.traceback = self.error

    @property
    def data(self):
        return self.message.get('data')

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
        self.timeout_start = time.time()
        self.timeout_value = sec

    def expire(self, sec):
        self.expire_start = time.time()
        self.expire_value = sec

    def prevent_done(self):
        self.is_prevent_done = True

    def done(self):
        self.is_done = True

    def done_callback(self, callback):
        self._done_callback = callback

    def run(self):
        if self.expire_value \
           and time.time() - self.expire_start >= self.expire_value:
            self.failed('Event expired', traceback=False)
            return
        if self.timeout_value \
           and time.time() - self.timeout_start < self.timeout_value:
            return
        if self.is_done:
            return
        if self.timeout_value:
            self.timeout_start = None
            self.timeout_value = None
        try:
            self.result = do_strict_action(self.action, self)
        except Exception as error:
            self.failed(error)
        if self.is_prevent_done:
            self.is_prevent_done = False
        else:
            self.done()
        if self.is_done:
            if self.is_success is None:
                self.is_success = True
            if self._done_callback:
                self._done_callback(self)


def test_event():
    pool = EventPool()
    event = Event({
            'action': 'state',
            'id': 'uuid_id',
            'data': {}
        },
        'socket_address'
    )
    assert pool.poll_timeout() == -1
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
    assert event.error == 'Event expired'
