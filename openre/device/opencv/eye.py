# -*- coding: utf-8 -*-
from openre.device import IOBase
import cv2
import numpy as np

def fisheye(layer, result, power, middle_x, middle_y):
    layer_shape = layer.shape
    layer_width = layer_shape[1]
    layer_height = layer_shape[0]
    result_shape = result.shape
    result_width = result_shape[1]
    result_height = result_shape[0]
    middle_res_x = result_width / 2
    middle_res_y = result_height / 2
    result[:] = 0
    min_y = middle_y - abs(middle_res_y) * power
    min_x = middle_x - abs(middle_res_x) * power
    max_y = middle_y + abs(middle_res_y) * power
    max_x = middle_x + abs(middle_res_x) * power
    #result[:] = layer[start_y:end_y:2, start_x:end_x:2]
    for y, row in enumerate(result):
        pos_y = middle_res_y - y
        ly = middle_y - (pos_y > 0 and 1 or -1) * abs(pos_y) * power
        if ly < 0:
            continue
        if ly >= layer_height:
            break
        for x, value in enumerate(row):
            pos_x = middle_res_x - x
            lx = middle_x - (pos_x > 0 and 1 or -1) * abs(pos_x) * power
            if lx < 0:
                continue
            if lx >= layer_width:
                break
            row[x] = layer[ly, lx]
    return ((int(min_x), int(min_y)), (int(max_x), int(max_y)))


class GrayEye(IOBase):
    def __init__(self, config):
        self.cap = None
        super(GrayEye, self).__init__(config)
        config = self.config
        device = config.get('device', -1)
        self.cap = cv2.VideoCapture(device)
        cv2.namedWindow('image')
        self.output = np.zeros((config['height'], config['width']), np.uint8)
        cap = self.cap
        self.cap_width = width = cap.get(3)
        self.cap_height = height = cap.get(4)
        cv2.createTrackbar('Power', 'image', 0, 2000, self.set_power)
        cv2.createTrackbar('X', 'image', 0, int(width - 1), self.set_center_x)
        cv2.createTrackbar('Y', 'image', 0, int(height - 1), self.set_center_y)
        self.set_power(140)
        #cap.set(3, 1280)
        #cap.set(4, 1024)
        self.center_x = int(width // 2)
        self.center_y = int(height // 2)

    def set_power(self, power):
        self.power = power / 100.0
        if self.power > 5.0:
            self.power = 5.0
        if self.power < 2.5:
            self.power = 2.5
        cv2.setTrackbarPos('Power', 'image', int(self.power * 100))

    def set_center_x(self, x):
        half = self.config['width'] * self.power / 2
        if x > self.cap_width - half - 1:
            x = self.cap_width - half - 1
        if x < half:
            x = half
        self.center_x = int(x)
        cv2.setTrackbarPos('X', 'image', int(self.center_x))

    def set_center_y(self, y):
        half = self.config['height'] * self.power / 2
        if y > self.cap_height - half - 1:
            y = self.cap_height - half - 1
        if y < half:
            y = half
        self.center_y = int(y)
        cv2.setTrackbarPos('Y', 'image', int(self.center_y))

    def data_to_send(self, domain):
        self.update()
        return self.output

    def update(self):
        cap = self.cap
        if not cap:
            # TODO: try to reconnect?
            return
        if hasattr(cap, 'isOpen') and not cap.isOpen():
            return
        ret, frame = cap.read()
        if not ret:
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        p1, p2 = fisheye(gray, self.output, self.power,
                         self.center_x, self.center_y)
        cv2.rectangle(frame, p1, p2, 127, 2)
        center_x = self.center_x
        center_y = self.center_y
        cv2.line(frame,
                 (center_x - 10, center_y), (center_x - 5, center_y), 127)
        cv2.line(frame,
                 (center_x + 5, center_y), (center_x + 10, center_y), 127)
        cv2.line(frame,
                 (center_x, center_y - 10), (center_x, center_y - 5), 127)
        cv2.line(frame,
                 (center_x, center_y + 5), (center_x, center_y + 10), 127)

        cv2.imshow('frame', self.output)
        cv2.imshow('image', frame)
        cv2.waitKey(1)

    def receive_data(self, domain, data):
        data = data[0][1]
        d = 15.0*25
        x = int(sum(sum(data[0:15,0:25]))) - int(sum(sum(data[0:15,25:])))
        x = int(x / d)
        self.set_center_x(self.center_x + x)
        y = int(sum(sum(data[15:30,0:25]))) - int(sum(sum(data[15:30,25:])))
        y = int(y / d)
        self.set_center_y(self.center_y + y)
        power = sum(sum(data[30:,0:25])) - sum(sum(data[30:,25:]))
        power = power / (30.0*25)
        self.set_power(100*self.power + power)
        #cv2.imshow('muscle', data)

    def clean(self):
        super(GrayEye, self).clean()
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
            self.cap = None
        cv2.destroyAllWindows()

