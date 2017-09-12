# -*- coding: utf-8 -*-
from enum import Enum
from error import error
from math import *
import sympy
import time
import signal

class text_calculator(object):
    @staticmethod
    def basic_calc(text, timeout=10, debug=False):
        result = ''
        
        if text_calculator.is_non_calc(text):
            return

        try:
            signal.signal(signal.SIGALRM, text_calculator.timeout_handle)
            signal.alarm(timeout)
            start_time = time.time()

            if 'result=' not in text:
                exec('result={}'.format(text))
            else:
                exec(text)

            end_time = time.time()
            signal.alarm(0)

            if isinstance(result, (float, int, long)):
                if len(text_calculator.remove_non_digit(text)) < 10:
                    if text != str(result):
                        return (result, end_time - start_time)
                else:
                    return (result, end_time - start_time)
            elif debug:
                text_calculator.print_debug_info(text, result)
        except Exception as ex:
            if debug:
                text_calculator.print_debug_info(text, result, ex)
            return 

    @staticmethod
    def sympy_calc(text, return_on_error=False, debug=False):
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

    @staticmethod
    def timeout_handle(signum, frame):
        error_text = 'Calculation Timeout.'
        raise Exception(error_text)

class calc_type(Enum):
    unknown = 0
    polynomial_factorization = 1
    algebraic_equations = 2