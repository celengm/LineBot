# coding: utf-8

import random

class random_drawer(object):
    @staticmethod
    def draw_number(start, end):
        start = int(start)
        end = int(end)
        return random.randint(start, end)
        
    @staticmethod
    def draw_text(text_list):
        random.shuffle(text_list)
        return random.choice(text_list)

    @staticmethod
    def draw_probability(probability):
        return random.random() <= probability
