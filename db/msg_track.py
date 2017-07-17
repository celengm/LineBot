# -*- coding: utf-8 -*-

import os, sys
from collections import defaultdict

import urlparse
import psycopg2
from sqlalchemy.exc import IntegrityError
import hashlib

import collections

class message_tracker(object):

    def __init__(self, scheme, db_url):
        urlparse.uses_netloc.append(scheme)
        self.url = urlparse.urlparse(db_url)
        self._set_connection()
        self.channel_id_length = 33




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



    @property
    def table_structure(self):
        cmd = u'CREATE TABLE msg_track( \
                    {} VARCHAR(33) PRIMARY KEY, \
                    {} INTEGER NOT NULL DEFAULT 0, \
                    {} INTEGER NOT NULL DEFAULT 0, \
                    {} INTEGER NOT NULL DEFAULT 0, \
                    {} INTEGER NOT NULL DEFAULT 0, \
                    {} INTEGER NOT NULL DEFAULT 0, \
                    {} INTEGER NOT NULL DEFAULT 0);'.format(*_col_list)
        return cmd

    def log_message_activity(self, cid, type_of_event):
        """
        Type of Event:
        1 = receive text message
        2 = receive text message and auto reply system has been triggered
        3 = receive sticker message
        4 = receive sticker message and auto reply system has been triggered
        5 = count of reply with text message
        6 = count of reply with sticker message

        None listed code of Type of Event and Illegal channel id length will raise ValueError.
        """
        if len(groupId) != self.channel_id_length:
            raise ValueError();
        else:
            if type_of_event == 1:
                column_to_add = msg_track_col.text_msg
                update_last_message_recv = True
            elif type_of_event == 2:
                column_to_add = msg_track_col.text_msg_trig
                update_last_message_recv = True
            elif type_of_event == 3:
                column_to_add = msg_track_col.stk_msg
                update_last_message_recv = True
            elif type_of_event == 4:
                column_to_add = msg_track_col.stk_msg_trig
                update_last_message_recv = True
            elif type_of_event == 5:
                column_to_add = msg_track_col.text_rep
                update_last_message_recv = False
            elif type_of_event == 6:
                column_to_add = msg_track_col.stk_rep
                update_last_message_recv = False
            else:
                raise ValueError();

            cmd = u'UPDATE msg_track SET %(col)s = %(col)s + 1{} WHERE cid = %(cid)s'.format(u', last_msg_recv = NOW()' if update_last_message_recv else u'')
            cmd_dict = {'cid': cid, 'col': column_to_add}
            self.sql_cmd(cmd, cmd_dict)
            return True
        
    def new_data(self, cid):
        if len(groupId) != self.channel_id_length:
            raise ValueError();
        else:
            cmd = u'INSERT INTO msg_track (cid) VALUES (%(cid)s)'
            cmd_dict = {'cid': cid}
            self.sql_cmd(cmd, cmd_dict)
            return True

    def count_sum(self):
        """
        Returns a dictionary contains data.

        Keys(Data Description): 
        text_msg = receive text message
        text_msg_trig = receive text message and auto reply system has been triggered
        stk_msg = receive sticker message
        stk_msg_trig = receive sticker message and auto reply system has been triggered
        text_rep = count of reply with text message
        stk_rep = count of reply with sticker message
        """
        results = defaultdict(int)

        cmd = u'SELECT SUM(text_msg), SUM(text_msg_trig), SUM(stk_msg), SUM(stk_msg_trig), SUM(text_rep), SUM(stk_rep) FROM msg_track'
        sql_result = self.sql_cmd_only(cmd)
        results['text_msg'] = sql_result[0]
        results['text_msg_trig'] = sql_result[1]
        results['stk_msg'] = sql_result[2]
        results['stk_msg_trig'] = sql_result[3]
        results['text_rep'] = sql_result[4]
        results['stk_rep'] = sql_result[5]
        return results



_col_list = ['cid', 
             'text_msg',  'text_msg_trig', 
             'stk_msg', 'stk_msg_trig', 
             'text_rep', 'stk_rep',
             'last_msg_recv']
_col_tuple = collections.namedtuple('msg_track_col', _col_list)
msg_track_col = _col_tuple(0, 1, 2, 3, 4, 5, 6, 7)