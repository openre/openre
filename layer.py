# -*- coding: utf-8 -*-
"""
Слой (Layer) - набор однотипных нейронов, организованных в двухмерный массив.
Количество рядов и столбцов может быть разным, слой не обязательно квадратный.
Размер разных слоев в одном домене может быть разным.
"""

class Layer(object):
    """
    Содержит в себе 2d массив однотипных нейронов.
    """
    def __init__(self, layer_id, threshold, relaxation):
        """
        id:             types.address - уникальный в пределах одного домена.
                        Принимает участие в формировании адреса нейрона.
        threshold:      types.threshold - если neuron.level больше
                        layer.threshold то происходит спайк. Не должен быть
                        больше чем максимум у синапса
        relaxation:     types.sinapse_level - на сколько снижается neuron.level
                        с каждым тиком (tick)
        total_spikes:   types.address - количество спайков в слое за последний
                        тик
        """
        self.id = layer_id
        self.threshold = threshold
        self.relaxation = relaxation
        self.total_spikes = 0
