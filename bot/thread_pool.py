# -*- coding: utf-8 -*-

import threading

# TODO: enqueue works, infinite loop to wait job and execute(?, http://www.devshed.com/c/a/python/basic-threading-in-python/)

class pool(object):
    def __init__(self, thread_count):
        self.thread_pool = [handle_thread() for i in range(thread_count)]

class handle_thread(threading.Thread):
    def run(self, handler, body, signature):
        handler.handle(body, signature)


