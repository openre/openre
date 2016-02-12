import cv
from openre.device.abstract import Device
import numpy
from openre import neurons

class Video(Device):
    pass

def test_video_device():
    from openre import OpenRE
    config = {
        'layers': [
            {
                'name': 'V1',
                'width': 20,
                'height': 20,
            },
        ],
        'domains': [
            {
                'name'        : 'D1',
                'device'    : {
                    'type': 'Video',
                    'width': 10,   # [c1 c3]
                    'height': 10,  # [c2 c4]
                },
                'layers': [
                    {'name': 'V1', 'source': 'c1', 'shape': [0, 0, 5, 5]},
                    {'name': 'V1', 'source': 'c2', 'shape': [0, 5, 5, 5]},
                    {'name': 'V1', 'source': 'c3', 'shape': [5, 0, 5, 5]},
                    {'name': 'V1', 'source': 'c4', 'shape': [5, 5, 5, 5]},
                ],
            },
            {
                'name'        : 'D2',
                'device'    : {
                    'type': 'OpenCL',
                },
                'layers'    : [
                    {'name': 'V1', 'source': 'c1', 'shape': [0, 0, 5, 5]},
                    {'name': 'V1', 'source': 'c2', 'shape': [0, 5, 5, 5]},
                    {'name': 'V1', 'source': 'c3', 'shape': [5, 0, 5, 5]},
                    {'name': 'V1', 'source': 'c4', 'shape': [5, 5, 5, 5]},
                ],
            },
        ],
    }
    ore = OpenRE(config)
    ore.deploy()

