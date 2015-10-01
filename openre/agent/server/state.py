# -*- coding: utf-8 -*-
import copy
import datetime
import os

class State(dict):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(State, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'is_loaded'):
            return
        self.is_loaded = True

    def default(self):
        return {}

    def __keytransform__(self, key):
        return str(key)

    def __getitem__(self, key):
        return copy.deepcopy(super(State, self).__getitem__(
            self.__keytransform__(key)))

    def __setitem__(self, key, value):
        if not isinstance(value, dict):
            raise ValueError('Value should be the instance of a dict')
        if key not in self:
            super(State, self).__setitem__(
                self.__keytransform__(key),
                self.default()
            )
        val = super(State, self).__getitem__(self.__keytransform__(key))
        for value_key in value.keys():
            if value_key not in val:
                continue
            val[value_key] = value[value_key]
        val['time'] = datetime.datetime.utcnow()

    def __contains__(self, key):
        return super(State, self).__contains__(self.__keytransform__(key))

def is_running(state):
    if state['status'] in ['exit', 'error', 'kill', 'clean']:
        return False
    if not state['pid']:
        return False
    try:
        os.kill(state['pid'], 0)
    except OSError:  #No process with locked PID
        return False
    return True

class ProcessState(State):
    def default(self):
        return {
            'status': 'unknown',
            'id': None,
            'name': '',
            'pid': 0,
            'time': datetime.datetime.utcnow(),
            'message': '',
        }

class DomainState(State):
    def default(self):
        """
        state:
            unknown - нет статуса
            blank - только запустился, ожидает команду
            config - загружен конфиг и создан эксземпляр класса OpenRE с
                локальными пустыми доменами
            create_layers - создание слоев
            count_synapses - подсчет синапсов
            create_neurons - создание нейронов
            create_synapses - создание синапсов
            create_indexes - создание индексов
            upload_data - зазрузка данных на устройство
            run - домен запущен
        status:
            running - задача выполняется
            pause - домен на паузе
            done - задача выполнена
            error - ошибка
        """
        return {
            'state': 'done',
            'status': 'unknown',
            'id': None,
            'name': '',
            'time': datetime.datetime.utcnow(),
            'message': '',
            'synapses_count': None,
        }


process_state = ProcessState()
domain_state = DomainState()
