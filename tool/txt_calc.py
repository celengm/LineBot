# -*- coding: utf-8 -*-
from enum import Enum
from error import error
from math import *
import sympy
import time
from multiprocessing import Process
import Queue

class text_calculator(object):
    def __init__(self):
        self._queue = Queue.Queue()

    def basic_calc(self, text, debug=False):
        if text_calculator.is_non_calc(text):
            return

        calc_proc = Process(target=self._exec_calc, args=(text, self._queue))

        start_time = time.time()

        calc_proc.start()
        result = self._queue.get(True, 15.0)
        calc_proc.join()

        end_time = time.time()

        if isinstance(result, (float, int, long)):
            if len(text_calculator.remove_non_digit(text)) < 10:
                if text != str(result):
                    return (result, end_time - start_time)
            else:
                return (result, end_time - start_time)
        elif debug:
            text_calculator.print_debug_info(text, result)
        

    def sympy_calc(self, text, return_on_error=False, debug=False):
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
                if len(text_calculator.remove_non_digit(text)) < 10:
                    if text != str(result):
                        return (result, end_time - start_time)
                else:
                    return (result, end_time - start_time)
            else:
                if debug:
                    text_calculator.print_debug_info(text, result)
                return  error.string_calculator.result_is_not_numeric(text) if return_on_error else None
        except Exception as ex:
            if debug:
                text_calculator.print_debug_info(text, result, ex)
            return error.string_calculator.error_on_calculating(ex) if return_on_error else None

    def _exec_calc(self, text, queue):
        try:
            if 'result=' not in text:
                exec('result={}'.format(text))
            else:
                exec(text)

            queue.put(result)

        except Queue.Empty:
            if debug:
                text_calculator.print_debug_info(text, result)
            queue.put(u'Calculation Timeout.')

        except Exception as ex:
            if debug:
                text_calculator.print_debug_info(text, result, ex)
            queue.put(None)

    @staticmethod
    def _polynomial_factorication(text):
        pass

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

    @staticmethod
    def print_debug_info(input_text, output, ex=None):
        print 'String math calculation failed:'
        print 'type of output: {}'.format(type(output))
        print 'Original Text:'
        print input_text.encode('utf-8')
        print 'Result variant:'
        print str(output).encode('utf-8')
        print 'Error:'
        print '' if ex is None else ex

    @staticmethod
    def calculate_type(text):
        if '=' in text:
            return calc_type.algebraic_equations
        else:
            return calc_type.polynomial_factorization

class calc_type(Enum):
    unknown = 0
    polynomial_factorization = 1
    algebraic_equations = 2