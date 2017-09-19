# -*- coding: utf-8 -*-

import os
import tempfile
import hashlib

class img_msg(object):
    def __init__(self, line_api, imgur_api, tmp_path, kw_dict):
        self._line_api = line_api
        self._imgur_api = imgur_api
        self._kw_dict = kw_dict

        self.tmp_path = tmp_path

    def image_sha224_of_message(self, line_msg):
        message_content = self._line_api.get_content(line_msg.id)
        for chunk in message_content.iter_content(4096):
            chunk_data = chunk
            break

        return hashlib.sha224(chunk_data).hexdigest()

    def upload_imgur(self, line_msg):
        message_content = self._line_api.get_content(line_msg.id)

        image_url = self._imgur_api.upload_content(message_content.content)

        return u'檔案已上傳至imgur。\nURL: {}'.format(image_url)
