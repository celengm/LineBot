# -*- coding: utf-8 -*-

import urlparse
import psycopg2
from sqlalchemy.exc import IntegrityError

class db_query_manager(object):
    def __init__(self, scheme, db_url):
        urlparse.uses_netloc.append(scheme)
        self.url = urlparse.urlparse(db_url)
        self.set_connection()

    def sql_cmd_only(self, cmd):
        return self.sql_cmd(cmd, None)

    def sql_cmd(self, cmd, dict):
        try:
            self.cur.execute(cmd, dict)
            result = self.cur.fetchall()
            self.conn.commit()
        except psycopg2.ProgrammingError as ex:
            if ex.message == 'no results to fetch':
                result = None
            elif ex.message == 'can\'t execute an empty query':
                result = None
            else:
                raise ex
        
        if result is not None:
            if len(result) > 0:
                return result
            else:
                return None
        else:
            return None


    def close_connection(self):
        self.cur.close()
        self.conn.close()

    def set_connection(self):
        self.conn = psycopg2.connect(
            database=self.url.path[1:],
            user=self.url.username,
            password=self.url.password,
            host=self.url.hostname,
            port=self.url.port
        )
        self.cur = self.conn.cursor()



