# -*- coding: utf-8 -*-

import os

import urlparse
import psycopg2

import collections

class kw_dict_mgr(object):


    def __init__(self, scheme, db_url):
        urlparse.uses_netloc.append(scheme)
        self.url = urlparse.urlparse(db_url)
        self._set_connection()


    def get_tables(self):
        cmd = u'SELECT * FROM pg_catalog.pg_tables'
        result = self.sql_cmd(cmd)
        return result


    def create_kwdict(self):
        cmd = u'CREATE TABLE keyword_dict( \
                    id SERIAL, keyword TEXT PRIMARY KEY, reply TEXT, \
                    creator TEXT NOT NULL, deleted BOOLEAN DEFAULT FALSE, used_time INTEGER NOT NULL) RETURNING *;'
        result = self.sql_cmd(cmd)
        return result


    def insert_keyword(self, keyword, reply, creator_id):
        cmd = u'INSERT INTO keyword_dict(keyword, reply, creator) \
               VALUES(\'{kw}\', \'{rep}\', \'{cid}\') RETURNING *;'.format(kw=keyword, rep=reply, cid=creator_id)
        result = self.sql_cmd(cmd, keyword, reply)[0]
        return result


    def get_reply(self, keyword):
        kw = keyword
        cmd = u'SELECT * FROM keyword_dict WHERE keyword = \'{kw}\' AND deleted = FALSE;'.format(kw=keyword)
        cmd_update = u'UPDATE keyword_dict SET used_time = used_time + 1 WHERE keyword = \'{kw}\''.format(kw=keyword)
        self.sql_cmd(cmd_update)
        result = self.sql_cmd(cmd, kw)
        if len(result) > 0:
            return result
        else:
            return None


    def get_info(self, keyword):
        kw = keyword
        cmd = u'SELECT * FROM keyword_dict WHERE keyword = \'{kw}\';'.format(kw=keyword)
        result = self.sql_cmd(cmd, kw)
        if len(result) > 0:
            return result
        else:
            return None


    def delete_keyword(self, keyword):
        cmd = u'UPDATE keyword_dict SET deleted = TRUE WHERE keyword = \'{kw}\' RETURNING *;'.format(kw=keyword)
        result = self.sql_cmd(cmd, keyword)
        if len(result) > 0:
            return result
        else:
            return None




    def sql_cmd(self, cmd):
        return sql_cmd(cmd, None)


    def sql_cmd(self, cmd, *args):
        self._set_connection()
        try:
            self.cur.execute(cmd, args)
            result = self.cur.fetchall()
        except psycopg2.Error as ex:
            self._close_connection()
            return str(ex.message)
        except Exception as ex:
            self._close_connection()
            return str(ex.message)
        
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


_col_tuple = collections.namedtuple('kwdict_col',
                                    ['id', 'keyword', 'reply', 'creator', 'deleted', 'used_time'])
kwdict_col = _col_tuple(0, 1, 2, 3, 4, 5)