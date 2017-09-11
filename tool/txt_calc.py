# -*- coding: utf-8 -*-
from math import *
import time

class text_calculator(object):
    @staticmethod
    def calc(text, debug=False):
        result = ''
        if text_calculator.is_non_calc(text):
            return
        try:
            start_time = time.time()

            if 'result=' not in text:
                exec('result={}'.format(text))
            else:
                exec(text)

            end_time = time.time()

            if isinstance(result, (float, int, long)):
                print result
                if len(text_calculator.remove_non_digit(text)) < 10:
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
                print str(result).encode('utf-8')
        except Exception as ex:
            if debug:
                print 'String math calculation failed:'
                print type(result)
                print 'Original Text:'
                print text.encode('utf-8')
                print 'Result variant:'
                print str(result).encode('utf-8')
                print 'Error:'
                print ex
            return 

    @staticmethod
    def remove_non_digit(text):
        import string
        allchars = ''.join(chr(i) for i in xrange(256))
        identity = string.maketrans('', '')
        nondigits = allchars.translate(identity, string.digits)
        text = str(text)
        return text.translate(identity, nondigits)

    @staticmethod
    def is_non_calc(text):
        return (text.startswith('0') and '.' not in text) or text.startswith('+') or text.endswith('.')

    @staticmethod
    def formula_to_py(text):
        regex = ur"([\d.]*)([\d]*[\w]*)([+\-*/]{1})"
        
        def add_star(match):
            if match.group(1) != '' and match.group(2) != '':
                return u'{}*{}{}'.format(match.group(1), match.group(2), match.group(3))
            else:
                return match.group()
        
        return re.sub(regex, add_star, text)