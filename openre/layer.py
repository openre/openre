# -*- coding: utf-8 -*-
"""
Содержит в себе 2d массив однотипных нейронов.
"""

class Layer(object):
    """
    Слой (Layer) - набор однотипных нейронов, организованных в двухмерный
    массив.  Количество рядов и столбцов может быть разным, слой не обязательно
    квадратный. Размер разных слоев в одном домене может быть разным.
    """
    def __init__(self, config):
        """
        id:             types.address - уникальный в пределах одного домена.
                        Принимает участие в формировании адреса нейрона.
        threshold:      types.threshold - если neuron.level больше
                        layer.threshold то происходит спайк. Не должен быть
                        больше чем максимум у синапса
        relaxation:     types.sinapse_level - на сколько снижается neuron.level
                        с каждым тиком (tick).
                        По умолчанию - 0.
        total_spikes:   types.address - количество спайков в слое за последний
                        тик
        """
        self.config = config
        self.id = self.config['id']
        self.threshold = self.config['threshold']
        self.relaxation = self.config.get('relaxation', 0)
        self.total_spikes = 0
