# -*- coding: utf-8 -*-

import urlparse
import psycopg2
from sqlalchemy.exc import IntegrityError
import traceback
import Queue
from threading import Thread

from bot import webpage_auto_gen 

class db_query_manager(object):
    def __init__(self, scheme, db_url, flask_app):
        urlparse.uses_netloc.append(scheme)

        self.url = urlparse.urlparse(db_url)
        self.set_connection()
        self._auto_gen = webpage_auto_gen.webpage(flask_app)
        self.work_queue = Queue.Queue()

    def sql_cmd_only(self, cmd):
        return self.sql_cmd(cmd, None)

    def sql_cmd(self, cmd, dict):
        self.work_queue.put(sql_query_obj(cmd, dict))
        sql_thread = threadWithReturn(target=self._query_worker)
        sql_thread.daemon = True
        sql_thread.run()
        return sql_thread.join()

    def _query_worker(self):
        query_obj = self.work_queue.get()

        cmd = query_obj.cmd
        dict = query_obj.dict

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
                self.work_queue.task_done()
                raise ex
        except psycopg2.InternalError as uiex:
            text = uiex.message
            text += u'\nSQL Query: {}'.format(cmd)
            text += u'\nSQL Parameter Dict: {}'.format(dict)

            result = None

            self._auto_gen.rec_error(text, traceback.format_exc().decode('utf-8'), u'(SQL DB)')
            self.close_connection()
            self.set_connection()
            self.sql_cmd(cmd, dict)
        except Exception as e:
            text = e.message
            text += u'\nSQL Query: {}'.format(cmd)
            text += u'\nSQL Parameter Dict: {}'.format(dict)

            result = None

            self._auto_gen.rec_error(text, traceback.format_exc().decode('utf-8'), u'(SQL DB)')
            self.work_queue.task_done()
            raise e
        
        self.work_queue.task_done()
        if result is not None:
            if len(result) > 0:
                return result
            else:
                return None
        else:
            return None


    def close_connection(self):
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


class sql_query_obj(object):
    def __init__(self, cmd, dict):
        self.cmd = cmd
        self.dict = dict

    @property
    def cmd(self):
        return self.cmd
    
    @property
    def dict(self):
        return self.dict


class threadWithReturn(Thread):
    def __init__(self, *args, **kwargs):
        super(threadWithReturn, self).__init__(*args, **kwargs)

        self._return = None

    def run(self):
        if self._Thread__target is not None:
            self._return = self._Thread__target(*self._Thread__args, **self._Thread__kwargs)

    def join(self, *args, **kwargs):
        super(threadWithReturn, self).join(*args, **kwargs)

        return self._return



