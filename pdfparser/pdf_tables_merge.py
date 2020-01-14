#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
 * Created by zbl on 18-12-12 下午3:52.
"""

import re


def merge_tables(all_tables, write_file=False):
    _table_content_html_lists = []
    first_lline, end_line = '', ''
    for index in range(len(all_tables)):
        _table_content_html = all_tables[index].strip()
        _table_content_html_list = _table_content_html.strip('\n').split('\n')
        if len(all_tables) == 1:
            _table_content_html_lists.extend(_table_content_html_list)
        else:
            if not first_lline and not end_line:
                first_lline, end_line = _table_content_html_list[0], _table_content_html_list[-1]
            _table_content_html_list = _table_content_html_list[1:-1]
            if index == 0:  # start
                _table_content_html_lists.extend(_table_content_html_list)
            else:
                rowspan_content_re = re.search('("|<tr><td)>(.*?)</td', _table_content_html_list[0])
                rowspan_num_re = re.search('rowspan="(\d+)"', _table_content_html_list[0])
                if rowspan_content_re and rowspan_num_re and rowspan_content_re.group(2):
                    _table_content_html_lists.extend(_table_content_html_list)
                else:
                    if rowspan_num_re:
                        add_num = 0
                        pre_index = 1
                        for pre_item in _table_content_html_lists[::-1]:
                            # print(pre_item)
                            pre_rowspan_num_re = re.search('rowspan="(\d+)"', pre_item)
                            if _table_content_html_list[0].count('<td') == pre_item.count('<td'):
                                add_num = int(rowspan_num_re.group(1)) + pre_index
                                break
                            if pre_rowspan_num_re:
                                add_num = int(pre_rowspan_num_re.group(1)) + int(rowspan_num_re.group(1))
                                break
                            pre_index += 1
                        # print(add_num, pre_index, _table_content_html_lists[-pre_index])
                        _table_content_html_list[0] = re.sub('<td rowspan="\d+"></td>', '', _table_content_html_list[0], 1)
                        if 'rowspan' in _table_content_html_lists[-pre_index]:
                            _table_content_html_lists[-pre_index] = re.sub('<td rowspan="\d+">', '<td rowspan="{0}">'.format(add_num), _table_content_html_lists[-pre_index], 1)
                        else:
                            _table_content_html_lists[-pre_index] = re.sub('<tr><td>', '<tr><td rowspan="{0}">'.format(add_num), _table_content_html_lists[-pre_index], 1)
                        _table_content_html_lists.extend(_table_content_html_list)
                    else:
                        add_num = 0
                        pre_index = 1
                        for pre_item in _table_content_html_lists[::-1]:
                            # print('111', pre_item)
                            pre_rowspan_num_re = re.search('rowspan="(\d+)"', pre_item)
                            if _table_content_html_list[0].count('<td') == pre_item.count('<td'):
                                add_num = pre_index + 1
                                break
                            if pre_rowspan_num_re:
                                add_num = int(pre_rowspan_num_re.group(1))
                                break
                            pre_index += 1
                        # print('111', add_num, pre_index, _table_content_html_lists[-pre_index])
                        pre_content = re.search('("|<tr><td)>(.*?)</td', _table_content_html_lists[-pre_index]).group(2)
                        if 'rowspan' in _table_content_html_lists[-pre_index]:
                            _table_content_html_list[0] = re.sub('<tr><td>(.*?)</td>', '<tr>', _table_content_html_list[0], 1)
                            _table_content_html_lists[-pre_index] = re.sub('<tr><td rowspan="\d+">(.*?)</td>', '<tr><td rowspan="{1}">{0}</td>'.format(pre_content + rowspan_content_re.group(2), add_num), _table_content_html_lists[-pre_index], 1)
                        else:
                            if not bool(rowspan_content_re.group(2)):
                                _table_content_html_list[0] = re.sub('<tr><td>(.*?)</td>', '<tr>', _table_content_html_list[0], 1)
                                _table_content_html_lists[-pre_index] = re.sub('<tr><td>(.*?)</td>', '<tr><td rowspan="{1}">{0}</td>'.format(pre_content+rowspan_content_re.group(2), add_num), _table_content_html_lists[-pre_index], 1)
                        _table_content_html_lists.extend(_table_content_html_list)
    _table_content_htmls = '\n'.join(_table_content_html_lists)
    if first_lline and end_line:
        _table_content_htmls = first_lline + '\n' + _table_content_htmls + '\n' + end_line
    content = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Table</title>
</head>
<body>
{table}
</body>
</html>'''.format(table=_table_content_htmls)
    if write_file:
        with open('./tmp_table.html', 'w') as fileIo:
            fileIo.write(content)
    return content
