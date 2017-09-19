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

        image_url = self._imgur_api.upload_content(message_content)

        return u'檔案已上傳至imgur。\nURL: {}'.format(image_url)

        #with tempfile.NamedTemporaryFile(dir=self.tmp_path, delete=False) as tf:
        #    for chunk in message_content.iter_content():
        #        tf.write(chunk)
        #    tempfile_path = tf.name

        #    dest_path = tempfile_path + '.jpg'
        #    dest_name = os.path.basename(dest_path)
        #    os.rename(tempfile_path, dest_path)

        #    imgur_url = self._imgur_api.upload(dest_path)

        #    #import binascii

        #    #with open(dest_path, 'rb') as f:
        #    #    hexdata = binascii.hexlify(f.read())
            
        #    #hexlist = map(''.join, zip(*[iter(hexdata)]*2))

        ##os.remove(dest_path)

        #return u'檔案已上傳至imgur。\nURL: {}'.format(imgur_url)
