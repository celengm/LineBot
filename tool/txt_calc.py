# -*- coding: utf-8 -*-
from math import *
import time

class text_calculator(object):
    @staticmethod
    def calc(text, debug=False):
        result = ''
        if (text.startswith('0') and '.' not in text) or text.startswith('+') or text.endswith('.'):
            return
        try:
            start_time = time.time()

            if 'result=' not in text:
                exec('result={}'.format(text))
            else:
                exec(text)

            end_time = time.time()

            if isinstance(result, (float, int, long)):
                if len(text_calculator.remove_non_digit(text)) > 10:  
                    if text != str(result):
                        return (result, end_time - start_time)
                else:
                    return (result, end_time - start_time)
                
            elif debug:
                print 'String math calculation failed:'
                print type(result)
                print 'Original Text:'
                print text.encode('utf-8')
                print 'Result variant:'
                print result.encode('utf-8')
        except:
            if debug:
                print 'String math calculation failed:'
                print type(result)
                print 'Original Text:'
                print text.encode('utf-8')
                print 'Result variant:'
                print result.encode('utf-8')
            return 

    @staticmethod
    def remove_non_digit(text):
        import string
        all = string.maketrans('','')
        nodigs = all.translate(all, string.digits)
        return text.translate(all, nodigs)
