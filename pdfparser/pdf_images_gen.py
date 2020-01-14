#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
 * Created by zbl on 18-12-12 上午10:10.
"""

import copy
from PIL import Image


def use_image_get_table_top_bottom(path):
    image = Image.open(path)
    width, height = image.size
    h_lines = []
    h_width_index = dict()
    for y in range(height):
        tmp_h_line = []
        for x in range(width):
            r, g, b = image.getpixel((x, y))
            if r == g == b != 255:
                tmp_h_line.append((x, y))
                # if len(tmp_h_line) == 0: tmp_h_line.append((x, y))
                # elif x-tmp_h_line[-1][0] == 1: tmp_h_line.append((x, y))
        if len(tmp_h_line) > 10: h_lines.append(tmp_h_line)

    for line in h_lines:
        width = line[-1][0] - line[0][0]
        if width not in h_width_index:
            h_width_index[width] = [[line[0], line[-1]]]
        else:
            pre_h_width_index = h_width_index[width][-1]
            if abs(pre_h_width_index[0][1] - line[0][1]) > 3:
                h_width_index[width].append([line[0], line[-1]])
    xs, ys = [], []
    for item in copy.deepcopy(h_width_index):
        if len(h_width_index[item]) == 1: del h_width_index[item]
        else:
            for _item in h_width_index[item]:
                x0, x1 = _item[0][0], _item[1][0]
                y0, y1 = _item[0][1], _item[1][1]
                if x0 not in xs:
                    xs.append(x0)
                if x1 not in xs:
                    xs.append(x1)
                if y0 not in ys:
                    ys.append(y0)
                if y0 not in ys:
                    ys.append(y0)
    if len(xs) == 0:
        return [0, 0], [0, 0]
    else:
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        # print x0, y0, x1, y1
        return [float(x0/2.), float(y0/2.)], [float(x1/2.)+3, float(y1/2.)+3]
