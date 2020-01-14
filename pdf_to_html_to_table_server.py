#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
 * Created by zbl on 18-12-24 上午10:25.
"""

import os
import json
import shutil
import base64
import argparse
import traceback
try:
    import urlparse
except:
    import urllib.parse as urlparse

import tornado.web
import tornado.gen
from tornado.web import HTTPError
from tornado.ioloop import IOLoop
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor

from ztools.logClient import Logger

from pdfparser.pdf_gen import parser

LOGGER = Logger(filename='pdf_to_html_to_table_server.log')


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default=13131, help="server port")
    return parser.parse_args()


class ParserPdf2TableHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(4)

    def __init__(self, application, request, **kwargs):
        super(ParserPdf2TableHandler, self).__init__(application, request, **kwargs)
        self.out_path = './tmp_out_dir/'
        # self.pdf2html_cmd = 'cd {out_path} && pdf2htmlEX -f {start_page} -l {end_page} --no-drm 1 --embed-css 0 --embed-image 0 {file_name}'
        self.content = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Title</title>
</head>
<body>
{table}
</body>
</html>
        '''
        self.pdf2html_cmd = 'cd {out_path} && docker run -i --rm -v `pwd`:/pdf bwits/pdf2htmlex pdf2htmlEX -f {start_page} -l {end_page} --no-drm 1 --embed-css 0 --embed-image 0 {file_name}'

    @tornado.gen.coroutine
    def post(self, *args, **kwargs):
        result = {}
        status = {"code": 200, "message": "success"}
        try:
            all_page_tables, pdf_name, html = yield self._get_request_arguments()
            if len(all_page_tables) == 0:
                status["code"] = 404
                status["message"] = 'not found'
            else:
                # result = {'all_page_tables_html': self.content.format(table='<br><br>'.join(all_page_tables)), 'pdf_name': pdf_name}
                result = {
                    'all_page_tables_html': html,
                    'all_table': all_page_tables,
                    'pdf_name': pdf_name
                }
        except HTTPError as e:
            status["code"] = e.status_code
            status["message"] = e.log_message
        except Exception as e:
            LOGGER.exception(traceback.format_exc())
            status["code"] = 500
            status["message"] = str(traceback.format_exc())
    
        result.update(status)

        self.write(result)

    def _pdf_to_html(self, return_data):
        all_page_tables = []
        if not return_data['save_flag']:
            return all_page_tables, ''
        else:
            cd_path = '{}{}/'.format(self.out_path, return_data['pdf_name'].replace('.pdf', ''))
            pdf_cmd = self.pdf2html_cmd.format(out_path=cd_path,
                                               start_page=return_data['start_page'],
                                               end_page=return_data['end_page'],
                                               file_name=return_data['pdf_name'])
            LOGGER.info(pdf_cmd)
            run_result = os.popen(pdf_cmd).read()
            all_page_tables, html = parser(cd_path, return_data['pdf_name'])
            shutil.rmtree(cd_path)
        return all_page_tables, return_data['pdf_name'], html

    @run_on_executor
    def _get_request_arguments(self):
        req_body = self.request.body
        return_data = {
            'save_flag': False
        }
        # 尝试 json 解码
        try:
            req_arguments = json.loads(req_body)
            pdf_data = req_arguments.get("pdf")
            pdf_name = req_arguments.get("pdfName")
            start_page = req_arguments.get("startPage")
            end_page = req_arguments.get("endPage")
            _tmp_out_path = '{}{}'.format(self.out_path, pdf_name.replace('.pdf', ''))
            if not os.path.exists(_tmp_out_path):
                os.makedirs(_tmp_out_path)
            with open('{}/{}'.format(_tmp_out_path, pdf_name), 'wb') as pdfIo:
                pdfIo.write(base64.b64decode(pdf_data))
            return_data.update({
                "save_flag": True,
                "pdf_name": pdf_name,
                "start_page": start_page,
                "end_page": end_page
            })
            LOGGER.info('{} save success.'.format(pdf_name))
        except:
            # 尝试 urlparse 解码
            try:
                req_arguments = urlparse.parse_qs(req_body.decode("utf-8"))
                _tmp_pdf_data = req_arguments.get("pdf", [])
                if len(_tmp_pdf_data) > 0:
                    pdf_data = _tmp_pdf_data[0]
                    pdf_name = req_arguments.get("pdfName", [])
                    start_page = req_arguments.get("startPage", [])
                    end_page = req_arguments.get("endPage", [])
                    _tmp_out_path = '{}{}'.format(self.out_path, pdf_name[0].replace('.pdf', ''))
                    if not os.path.exists(_tmp_out_path):
                        os.makedirs(_tmp_out_path)
                    with open('{}/{}'.format(_tmp_out_path, pdf_name[0]), 'wb') as pdfIo:
                        pdfIo.write(base64.b64decode(pdf_data))
                    return_data.update({
                        "save_flag": True,
                        "pdf_name": pdf_name[0],
                        "start_page": start_page[0],
                        "end_page": end_page[0]
                    })
                    LOGGER.info('{} save success.'.format(pdf_name[0]))
            except:
                LOGGER.error(traceback.format_exc())

        return self._pdf_to_html(return_data)


if __name__ == '__main__':
    args = get_args()

    HANDLERS = [
        (r'/parser/pdf2table', ParserPdf2TableHandler),
    ]

    app = tornado.web.Application(HANDLERS, debug=False)
    app.listen(args.port, address='0.0.0.0')
    LOGGER.info('tornado server started on port {port}'.format(port=args.port))
    IOLoop.current().start()
