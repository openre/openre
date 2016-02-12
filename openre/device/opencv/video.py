import cv

def test_video_device():
    from openre import OpenRE
    config = {
        'layers': [
            {
                'name': 'R1',
                'width': 20,
                'height': 20,
                'is_inhibitory': False,
                'connect': [
                    {
                        'name': 'V2',
                        'radius': 1,
                        'shift': [0, 0],
                    },
                ],
            },
            {
                'name': 'V2',
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
                    'data': [
                        {'name': 'c1', 'shape': [0, 0, 5, 5]},
                        {'name': 'c2', 'shape': [0, 5, 5, 5]},
                        {'name': 'c3', 'shape': [5, 0, 5, 5]},
                        {'name': 'c4', 'shape': [5, 5, 5, 5]},
                    ],
                },
            },
            {
                'name'        : 'D2',
                'device'    : {
                    'type': 'OpenCL',
                },
                'layers'    : [
                    {'name': 'V2'},
                ],
            },
        ],
    }
    ore = OpenRE(config)
    ore.deploy()

