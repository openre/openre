# -*- coding: utf-8 -*-
import copy
import datetime
import os

class State(dict):
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
        if state['pid'] == 0 and state['was_pid'] != 0:
            pass
        else:
            return False
    if not state['pid'] and not state['was_pid']:
        return False
    try:
        if state['pid']:
            os.kill(state['pid'], 0)
        elif state['was_pid']:
            os.kill(state['was_pid'], 0)
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
            'was_pid': 0,
            'time': datetime.datetime.utcnow(),
            'message': '',
        }

class DomainState(State):
    def default(self):
        """
        state:
            unknown - нет статуса
            blank - только запустился, ожидает команду
            config - загружен конфиг и создан эксземпляр класса OpenRE
            deploy_domains - создание пустых доменов с указанием какие из них
                должны быть локальными
            deploy_layers - создание слоев
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
