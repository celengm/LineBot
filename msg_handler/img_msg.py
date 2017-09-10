# -*- coding: utf-8 -*-

import os
import tempfile

class img_msg(object):
    def __init__(self, line_api, imgur_api, tmp_path):
        self._line_api = line_api
        self._imgur_api = imgur_api

        self.tmp_path = tmp_path

    def image_handle(msg):
        message_content = self._line_api.get_content(msg.id)

        with tempfile.NamedTemporaryFile(dir=self.tmp_path, delete=False) as tf:
            for chunk in message_content.iter_content():
                print len(chunk)
                tf.write(chunk)
            tempfile_path = tf.name

            dest_path = tempfile_path + '.jpg'
            dest_name = os.path.basename(dest_path)
            os.rename(tempfile_path, dest_path)

        os.remove(dest_path)

        return u'GET'

    def upload_imgur(line_msg):
        message_content = self._line_api.get_content(line_msg.id)

        with tempfile.NamedTemporaryFile(dir=self.tmp_path, delete=False) as tf:
            for chunk in message_content.iter_content():
                tf.write(chunk)
            tempfile_path = tf.name

            dest_path = tempfile_path + '.jpg'
            dest_name = os.path.basename(dest_path)
            os.rename(tempfile_path, dest_path)

            imgur_url = self.imgur_api.upload(dest_path)

            import binascii

            with open(dest_path, 'rb') as f:
                hexdata = binascii.hexlify(f.read())
            
            hexlist = map(''.join, zip(*[iter(hexdata)]*2))

        os.remove(dest_path)

        return u'檔案已上傳至imgur。\nURL: {}'.format(imgur_url)
