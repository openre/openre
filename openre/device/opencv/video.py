import cv2
from openre.device.iobase import IOBase
import numpy
from openre import neurons

class GrayVideo(IOBase):
    def __init__(self, config):
        super(GrayVideo, self).__init__(config)
        config = self.config
        device = config.get('device', -1)
        self.cap = cv2.VideoCapture(device)
        cap = self.cap
        if config.get('window'):
            cv2.namedWindow(config['window'])
        cap.set(3, config['width'])
        cap.set(4, config['height'])
        config['cap_width'] = cap.get(3)
        config['cap_height'] = cap.get(3)
        config['resize'] = False
        if config['cap_width'] != config['width'] \
           or config['cap_height'] != config['height']:
            config['resize'] = True

    def data_to_send(self, domain):
        cap = self.cap
        if not cap:
            # TODO: try to reconnect?
            return
        if hasattr(cap, 'isOpen') and not cap.isOpen():
            return
        config = self.config
        ret, frame = cap.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if config['resize']:
            gray = cv2.resize(gray, (config['width'], config['height']),
                                interpolation=cv2.INTER_CUBIC)
        if config.get('window'):
            cv2.imshow(config['window'], gray)
            cv2.waitKey(1)
        return gray


def test_camera():
    from openre import OpenRE
    import os
    config = {
        'layers': [
            {
                'name': 'V1',
                'width': 16,
                'height': 10,
            },
        ],
        'domains': [
            {
                'name'        : 'Camera',
                'device'    : {
                    'type': 'GrayVideo',
                    'device': os.path.join(
                        os.path.dirname(__file__),
                        './templates/device/camera-test.avi'
                    ),
                    'width': 16,
                    'height': 10,
                    #'window': 'Cam input',
                },
                'sources': [
                    # [c1 c2]
                    # [c3 c4]
                    {'name': 'c1', 'shape': [0, 0, 8, 5]},
                    {'name': 'c2', 'shape': [8, 0, 8, 5]},
                    {'name': 'c3', 'shape': [0, 5, 8, 5]},
                    {'name': 'c4', 'shape': [8, 5, 8, 5]},
                ],
            },
            {
                'name'        : 'D2',
                'device'    : {
                    'type': 'OpenCL',
                },
                'layers'    : [
                    {'name': 'V1', 'input': 'c1', 'shape': [0, 0, 8, 5]},
                    {'name': 'V1', 'input': 'c2', 'shape': [8, 0, 8, 5]},
                    {'name': 'V1', 'input': 'c3', 'shape': [0, 5, 8, 5]},
                    {'name': 'V1', 'input': 'c4', 'shape': [8, 5, 8, 5]},
                ],
            },
        ],
    }
    ore = OpenRE(config)
    ore.deploy()
    device1 = ore.domains[0].device
    device2 = ore.domains[1].device
    D1 = ore.domains[0]
    D2 = ore.domains[1]
    D2.neurons.level.data[:] = 0
    assert sum(D2.neurons.level.data) == 0
    D2.neurons.level.to_device(device2)
    ore.tick()
    D1.neurons.from_device(device1)
    D2.neurons.from_device(device2)
    arr = D2.neurons.level.data
    a1 = arr[0:40]
    a2 = arr[40:80]
    a3 = arr[80:120]
    a4 = arr[120:160]
    check = numpy.array(
        [[  0,   0,   0,   0,   0,   0,   0,   0,  20,  20,  20,  20,  20,  20,  20,  20],
         [  0,   0,   0,   0,   0,   0,   0,   0,  20,  20,  20,  20,  20,  20,  20,  20],
         [  2,   2,   2,   2,   2,   2,   2,   2,  21,  21,  21,  21,  21,  21,  21,  21],
         [  2,   2,   2,   2,   2,   2,   2,   2,  21,  21,  21,  21,  21,  21,  21,  21],
         [ 19,  19,  19,  19,  19,  19,  19,  19,  19,  19,  19,  19,  19,  19,  19,  19],
         [115, 115, 115, 115, 115, 115, 115, 115, 245, 245, 245, 245, 245, 245, 245, 245],
         [116, 116, 116, 116, 116, 116, 116, 116, 254, 254, 254, 254, 254, 254, 254, 254],
         [116, 116, 116, 116, 116, 116, 116, 116, 254, 254, 254, 254, 254, 254, 254, 254],
         [114, 114, 114, 114, 114, 114, 114, 114, 255, 255, 255, 255, 255, 255, 255, 255],
         [114, 114, 114, 114, 114, 114, 114, 114, 255, 255, 255, 255, 255, 255, 255, 255],],
        dtype=numpy.uint8
    )
    assert list(numpy.ravel(check[0:5, 0:8])) == list(a1)
    assert list(numpy.ravel(check[0:5, 8:16])) == list(a2)
    assert list(numpy.ravel(check[5:10, 0:8])) == list(a3)
    assert list(numpy.ravel(check[5:10, 8:16])) == list(a4)
    assert sum(D2.neurons.level.data) > 0
