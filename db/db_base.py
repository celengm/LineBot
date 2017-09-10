# -*- coding: utf-8 -*-

import urlparse
import psycopg2
from sqlalchemy.exc import IntegrityError

class db_base_obj(object):
    def __init__(self, scheme, db_url):
        urlparse.uses_netloc.append(scheme)
        self.url = urlparse.urlparse(db_url)
        self._set_connection()

    def sql_cmd_only(self, cmd):
        return self.sql_cmd(cmd, None)

    def sql_cmd(self, cmd, dict):
        self._set_connection()
        self.cur.execute(cmd, dict)
        try:
            result = self.cur.fetchall()
        except psycopg2.ProgrammingError as ex:
            if ex.message == 'no results to fetch':
                result = None
            else:
                raise ex
        
        self._close_connection()
        return result


    def _close_connection(self):
        self.conn.commit()
        self.cur.close()
        self.conn.close()

    def _set_connection(self):
        self.conn = psycopg2.connect(
            database=self.url.path[1:],
            user=self.url.username,
            password=self.url.password,
            host=self.url.hostname,
            port=self.url.port
        )
        self.cur = self.conn.cursor()


