#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
 * Created by zbl on 18-12-10 上午10:56.
 * 依赖pdf2htmlEX 解析pdf 文件，主要是table
"""

import os

import bs4
import numpy as np
from bs4 import BeautifulSoup

from pdfparser.pdf_tables_merge import merge_tables
from pdfparser.pdf_images_gen import use_image_get_table_top_bottom


def find_position(remaining_row_list, coord_index_dict, index_coord_dict):
    position_found_dict = dict()
    for cell in remaining_row_list:
        position_found_dict[cell] = []
        cell_bbox, cell_text = cell
        x_bottom, x_top, y_bottom, y_top = cell_bbox
        for coord in coord_index_dict:
            _x_bottom, _x_top, _y_bottom, _y_top = coord
            flag = 0
            if x_top == _x_top:
                flag += 1
            if y_top == _y_top:
                flag += 1
            if x_bottom == _x_bottom:
                flag += 1
            if y_bottom == _y_bottom:
                flag += 1

            if flag == 2 and _y_top > y_top and _y_bottom < y_bottom:
                if coord not in position_found_dict[cell]:
                    position_found_dict[cell].append(coord)
            if flag == 2 and _x_top > x_top and _x_bottom < x_bottom:
                if coord not in position_found_dict[cell]:
                    position_found_dict[cell].append(coord)
            if flag == 3:
                position_found_dict[cell].append(coord)

    for cell in position_found_dict:
        cell_bbox, cell_text = cell
        coord_list = position_found_dict[cell]
        x_top_coord_list = [coord[1] for coord in coord_list]
        y_top_coord_list = [coord[3] for coord in coord_list]
        x_bottom_coord_list = [coord[0] for coord in coord_list]
        y_bottom_coord_list = [coord[2] for coord in coord_list]
        x_top_coord_list = sorted(x_top_coord_list)
        y_top_coord_list = sorted(y_top_coord_list)
        x_bottom_coord_list = sorted(x_bottom_coord_list)
        y_bottom_coord_list = sorted(y_bottom_coord_list)

        if not x_top_coord_list or not x_bottom_coord_list or not y_top_coord_list or not y_bottom_coord_list:
            continue
        combined_cell_bbox = (x_bottom_coord_list[0],
                              x_top_coord_list[-1],
                              y_bottom_coord_list[-1],
                              y_top_coord_list[0])
        if cell_bbox == combined_cell_bbox:
            combined_cell_bbox = (x_bottom_coord_list[0],
                                  x_top_coord_list[0],
                                  y_bottom_coord_list[0],
                                  y_top_coord_list[0])

            if combined_cell_bbox in coord_index_dict:
                tag = ''
                if len(set(x_top_coord_list)) == 1 and len(set(y_top_coord_list)) > 1:
                    tag = 'y%s' % len(set(y_top_coord_list))
                elif len(set(x_top_coord_list)) > 1 and len(set(y_top_coord_list)) == 1:
                    tag = 'x%s' % len(set(x_top_coord_list))
                if tag != '':
                    index_coord_dict[coord_index_dict[combined_cell_bbox]] = [tag, cell_text]

    for cell in index_coord_dict:
        if isinstance(index_coord_dict[cell], tuple):
            index_coord_dict[cell] = ['none', '']
    return index_coord_dict


def pretreatment_dict(index_coord_dict, num_of_rows, num_of_cols):
    # 先判断 none 类型的是否真的被rowspan 覆盖
    # 先将rowspan, colspan覆盖的范围取出
    colspan_range = []
    rowspan_range = []
    for i in range(num_of_rows):
        for j in range(num_of_cols):
            content_complex = index_coord_dict[(j, i)]
            cell_tag = content_complex[0]
            if cell_tag.startswith('x'):
                cell_tag = int(cell_tag.replace('x', ''))
                colspan_range.append((i, [j, j + cell_tag - 1]))
            elif cell_tag.startswith('y'):
                cell_tag = int(cell_tag.replace('y', ''))
                rowspan_range.append((j, [i, i + cell_tag - 1]))
    if not rowspan_range:
        rowspan_range.append((0, [num_of_rows, num_of_rows]))
    if not colspan_range:
        colspan_range.append((0, [num_of_cols, num_of_cols]))
    # 记录被修改的位置然后合并
    colspan_clean_index = dict()
    rowspan_clean_index = dict()
    index_coord_dict_backup = dict()
    for i in range(num_of_rows):
        for j in range(num_of_cols):
            content_complex = index_coord_dict[(j, i)]
            cell_tag = content_complex[0]
            # 预先处理 'none'
            if cell_tag == 'none':
                c_flag, tmp_c_flag = 0, 0
                tmp_colspan_clean_index = []
                for colspan in colspan_range:
                    if i == colspan[0]:
                        tmp_c_flag += 1
                        if colspan[1][0] > j or j > colspan[1][1]:
                            c_flag += 1
                            if (j, i) not in tmp_colspan_clean_index: tmp_colspan_clean_index.append((j, i))
                if c_flag == tmp_c_flag and c_flag != 0:
                    cell_tag = 'single'
                    for item in tmp_colspan_clean_index:
                        if item[1] in colspan_clean_index.keys():
                            colspan_clean_index[item[1]].append(item)
                        else:
                            colspan_clean_index[item[1]] = [item]
                else:
                    r_flag, tmp_r_flag = 0, 0
                    tmp_rowspan_clean_index = []
                    for rowspan in rowspan_range:
                        if j == rowspan[0]:
                            tmp_r_flag += 1
                            if rowspan[1][0] > i or i > rowspan[1][1]:
                                r_flag += 1
                                if (j, i) not in tmp_rowspan_clean_index: tmp_rowspan_clean_index.append((j, i))
                    if r_flag == tmp_r_flag and r_flag != 0:
                        # cell_tag = 'single'
                        for item in tmp_rowspan_clean_index:
                            if item[0] in rowspan_clean_index.keys():
                                rowspan_clean_index[item[0]].append(item)
                            else:
                                rowspan_clean_index[item[0]] = [item]

            content_complex[0] = cell_tag
            index_coord_dict_backup[(j, i)] = content_complex

    # TODO: 以下只处理了列，行还未处理(未遇到)
    # for y_key in colspan_clean_index:
    #     x_y_index = rowspan_clean_index[y_key]
    #     tmp_x = []
    #     for index in x_y_index:
    #         if len(tmp_x) == 0:
    #             tmp_x.append([index[1], index[1]])
    #         else:
    #             if index[1] - tmp_x[-1][1] != 1:
    #                 tmp_x.append([index[1], index[1]])
    #             else:
    #                 tmp_y[-1] = [tmp_x[-1][0], index[1]]
    #     for ys in tmp_x:
    #         _tmp_x = tmp_x
    #         if ys[0] == 0:
    #             _tmp_tag = 'y{0}'.format(ys[1]+1)
    #             index_coord_dict_backup[(x_key, ys[0])][0] = _tmp_tag
    #         else:
    #             _tmp_y = ys[0]-1
    #             _tmp_tag = 'y{0}'.format(ys[1]-ys[0]+2)
    #             _tmp_pre_content = index_coord_dict_backup[(_tmp_x, _tmp_y)][1].strip()
    #             if len(_tmp_pre_content) == 0:
    #                 index_coord_dict_backup[(x_key, _tmp_y)][0] = _tmp_tag
    #             else:
    #                 index_coord_dict_backup[(x_key, ys[0])][0] = 'y{0}'.format(ys[1]-ys[0]+1)

    for x_key in rowspan_clean_index:
        x_y_index = rowspan_clean_index[x_key]
        tmp_y = []
        for index in x_y_index:
            if len(tmp_y) == 0:
                tmp_y.append([index[1], index[1]])
            else:
                if index[1] - tmp_y[-1][1] != 1:
                    tmp_y.append([index[1], index[1]])
                else:
                    tmp_y[-1] = [tmp_y[-1][0], index[1]]
        for ys in tmp_y:
            _tmp_x = x_key
            if ys[0] == 0:
                _tmp_tag = 'y{0}'.format(ys[1]+1)
                index_coord_dict_backup[(x_key, ys[0])][0] = _tmp_tag
            else:
                _tmp_y = ys[0]-1
                _tmp_tag = 'y{0}'.format(ys[1]-ys[0]+2)
                _tmp_pre_content = index_coord_dict_backup[(_tmp_x, _tmp_y)][1].strip()
                if len(_tmp_pre_content) == 0:
                    index_coord_dict_backup[(x_key, _tmp_y)][0] = _tmp_tag
                else:
                    index_coord_dict_backup[(x_key, ys[0])][0] = 'y{0}'.format(ys[1]-ys[0]+1)
    # print colspan_clean_index
    # print rowspan_clean_index
    return index_coord_dict_backup


def output_to_html(index_coord_dict, num_of_rows, num_of_cols):
    index_coord_dict = pretreatment_dict(index_coord_dict, num_of_rows, num_of_cols)
    tag = np.zeros(shape=(num_of_rows, num_of_cols), dtype=int)
    for index in index_coord_dict:
        if index_coord_dict[index][0] != 'none':
            tag[index[1], index[0]] = 1

    html_script = '<table border="1" cellspacing="0" width="50%" height="150">\n'
    for i in range(num_of_rows):
        html_row = '<tr>'
        for j in range(num_of_cols):
            content_complex = index_coord_dict[(j, i)]
            cell_content = content_complex[1]
            cell_tag = content_complex[0]
            if len(cell_content.strip()) == 0:
                cell_content = '--'

            if cell_tag == 'single':
                html_row += '<td>%s</td>' % cell_content
            elif cell_tag.startswith('x'):
                cell_tag = int(cell_tag.replace('x', ''))
                html_row += '<td colspan="%s">%s</td>' % (cell_tag, cell_content)
            elif cell_tag.startswith('y'):
                cell_tag = int(cell_tag.replace('y', ''))
                html_row += '<td rowspan="%s">%s</td>' % (cell_tag, cell_content)

        html_row += '</tr>'
        html_script += html_row + '\n'
    html_script += '</table>'
    return html_script


def use_css_get_xy(__css, _cell):
    _cell_class = _cell.get('class')
    _cell_class = _cell_class[1:]
    _cell_size = [__css[item] for item in _cell_class]
    # print(_cell_size)
    _cell_size = [
        _cell_size[0]['left'].replace('pt', '').replace('px', ''),
        _cell_size[1]['bottom'].replace('pt', '').replace('px', ''),
        _cell_size[2]['width'].replace('pt', '').replace('px', ''),
        _cell_size[3]['height'].replace('pt', '').replace('px', '')]
    _cell_size = [int(round(float(item))) for item in _cell_size]
    height = int(round(float(__css['h0']['height'].replace('pt', '').replace('px', ''))))

    x_bottom = _cell_size[0]  # x0
    x_top = _cell_size[0] + _cell_size[2]  # x1
    y_bottom = height - _cell_size[1]  # y1
    y_top = height - (_cell_size[1] + _cell_size[3])  # y0
    return x_bottom, x_top, y_bottom, y_top


def find_tables(_root_path, _css, _sections, img_path, img_xy):
    _tables = []
    _table = []
    tag = 0
    for _section in _sections:
        _section_class = _section.get('class')
        if len(_section_class) < 4:
            continue
        if _section_class[0] == 'c':
            if tag == 0:
                tag = 1

        elif _section_class[0] != 'c':
            tag = 0
            if _table:
                _tables.append(_table)
            _table = []

        if tag == 1:
            _table.append(_section)
    if _table:
        _tables.append(_table)

    html_tables = []
    if not img_path:
        xy0, xy1 = [0, 0], [0, 0]
    else:
        xy0, xy1 = use_image_get_table_top_bottom('{}{}'.format(_root_path, img_path))
        xy0[0], xy0[1], xy1[0], xy1[1] = xy0[0]+img_xy[0][0], xy0[1]+img_xy[0][1], img_xy[1][0], img_xy[1][1]
    if xy0[0] == 0 and xy0[1] == 0 and xy1[0] == 0 and xy1[1] == 0: return html_tables
    for _table in _tables:
        x_collection = []
        y_collection = []
        cell_text_dict = dict()

        for _cell in _table:
            text = _cell.text
            # x0, x1, y1, y0
            x_bottom, x_top, y_bottom, y_top = use_css_get_xy(_css, _cell)
            if y_top < xy0[1] or y_bottom > xy1[1]: continue

            x_collection.append(x_bottom)
            x_collection.append(x_top)
            y_collection.append(y_bottom)
            y_collection.append(y_top)

            cell_text_dict[(x_bottom, x_top, y_bottom, y_top)] = text
        if not cell_text_dict: continue
        x_collection = set(x_collection)
        x_collection = sorted(x_collection)

        y_collection = set(y_collection)
        y_collection = sorted(y_collection)

        x_map = dict()
        y_map = dict()
        x_collection_backup = []
        y_collection_backup = []
        for item in x_collection:
            tag = False
            for xx in x_collection_backup:
                if abs(item - xx) <= 3:
                    tag = True
                    x_map[item] = xx
                    break
            if not tag:
                x_map[item] = item
                x_collection_backup.append(item)

        for item in y_collection:
            tag = False
            for xx in y_collection_backup:
                if abs(item - xx) <= 3:
                    tag = True
                    y_map[item] = xx
                    break
            if not tag:
                y_map[item] = item
                y_collection_backup.append(item)

        x_collection = x_collection_backup
        y_collection = y_collection_backup

        cell_text_dict_backup = dict()
        for item in cell_text_dict:
            text = cell_text_dict[item]
            x_bottom, x_top, y_bottom, y_top = item
            cell_text_dict_backup[(x_map[x_bottom], x_map[x_top], y_map[y_bottom], y_map[y_top])] = text

        cell_text_dict = cell_text_dict_backup

        index_coord_dict = dict()
        coord_index_dict = dict()
        # 组装规则矩阵
        for i, _x in enumerate(x_collection):
            if i == len(x_collection) - 1:
                continue
            for j, _y in enumerate(y_collection):
                if j == len(y_collection) - 1:
                    continue
                coord = (_x, x_collection[i + 1], y_collection[j + 1], _y)
                index_coord_dict[(i, j)] = coord
                coord_index_dict[coord] = (i, j)

        remaining_cell_text_list = []
        for cell_bbox in cell_text_dict:
            cell_text = cell_text_dict[cell_bbox]
            if cell_bbox is None:
                continue
            cell_bbox = tuple(cell_bbox)
            if cell_bbox in coord_index_dict:
                index_coord_dict[coord_index_dict[cell_bbox]] = ['single', cell_text]
            else:
                remaining_cell_text_list.append((cell_bbox, cell_text))

        if remaining_cell_text_list:
            index_coord_dict = find_position(remaining_cell_text_list, coord_index_dict, index_coord_dict)

        # 处理元组情况
        for item in index_coord_dict:
            if isinstance(index_coord_dict[item], tuple):
                index_coord_dict[item] = ['none', '']
        tmp_html = output_to_html(index_coord_dict, len(y_collection) - 1, len(x_collection) - 1)
        # print tmp_html
        html_tables.append(tmp_html)
    return html_tables


def pdf_to_html(out_path, file_path, file_name, start_page, end_page):
    if not os.path.exists(out_path):
        os.mkdir(out_path)
    pdf2html_cmd = 'cd {out_path} && cp {cp_s} {cp_e} && docker run -i --rm -v `pwd`:/pdf bwits/pdf2htmlex pdf2htmlEX -f {start_page} -l {end_page} --no-drm 1 --embed-css 0 --embed-image 0 {file_name}'
    run_result = os.popen(pdf2html_cmd.format(out_path=out_path, cp_s=file_path+file_name, cp_e='./', start_page=start_page, end_page=end_page, file_name=file_name)).read()
    print(run_result)


def parser(root_path, file_name):
    html_f = root_path + file_name.replace('pdf', 'html')
    css_f = root_path + file_name.replace('pdf', 'css')

    html = ''
    with open(html_f, 'rU') as handle:
        html = handle.readlines()
    html = ''.join(html)

    css = dict()
    with open(css_f, 'rU') as handle:
        for line in handle:
            line = line.strip()
            if not line.startswith('.'):
                continue
            line = line.split('{')
            if not line:
                continue
            if len(line) != 2:
                continue
            name = line[0].strip('.')
            if name not in css:
                css[name] = dict()
            else:
                continue
            attributes = line[1].replace('}', '')
            attributes = attributes.split(';')
            for attribute in attributes:
                attribute = attribute.strip()
                if attribute != '':
                    attribute = attribute.split(':')
                    if len(attribute) != 2:
                        continue
                    attribute_name = attribute[0]
                    attribute_attribute = attribute[1]
                    css[name][attribute_name] = attribute_attribute

    html = BeautifulSoup(html, "lxml")
    html = html.body
    all_pages = html.select('#page-container')
    all_pages = all_pages[0]
    all_page_tables = []
    for singe_page in all_pages.contents:
        if isinstance(singe_page, bs4.element.NavigableString):
            continue
        if not singe_page.img:
            back_img = None
            back_img_xy = []
        else:
            back_img = singe_page.img.attrs.get('src', '')
            x_bottom, x_top, y_bottom, y_top = use_css_get_xy(css, singe_page.img.attrs)
            back_img_xy = [(x_bottom, y_top), (x_top, y_bottom)]
        sections = singe_page.contents
        for section in sections:
            section_class = section.get('class')
            if not section_class:
                continue
            if len(section_class) == 1:
                continue

            subsections = section.contents
            single_page_tables = find_tables(root_path, css, subsections, back_img, back_img_xy)
            if len(single_page_tables) != 0:
                all_page_tables.extend(single_page_tables)
    return all_page_tables, merge_tables(all_page_tables)

# if __name__ == '__main__':
#     root_path, file_name = '', ''
#     parser(root_path, file_name)
