# -*- coding: utf-8 -*-
"""
Содержит в себе слои и синапсы.
"""

class Domain(object):
    """
    id:                 types.address - должен быть уникальным для всех доменов
    tick:               types.tick - номер тика с момента запуска. При 32 битах
                        и 1000 тиков в секунду переполнение произойдет через
                        49 дней. При 64 битах через 584 млн. лет.
    learn_threshold:    types.tick - как близко друг к другу по времени должен
                        сработать pre и post нейрон, что бы поменялся вес
                        синапса в большую сторону
    forget_threshold:   types.tick - насколько сильной должна быть разница между
                        pre.tick и post.tick что бы уменьшился вес синапса.
    total_spikes:       types.address - количество спайков в домене за последний
                        тик
    Жеательно что бы выполнялось условие:
        0 <= learn_threshold <= forget_threshold <= types.tick.max
    """
    def __init__(self, domain_id, learn_threshold=0, forget_threshold=0):
        self.id = domain_id
        self.tick = 0
        self.learn_threshold = learn_threshold
        self.forget_threshold = forget_threshold
        self.total_spikes = 0
