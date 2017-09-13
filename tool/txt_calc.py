# -*- coding: utf-8 -*-
from multiprocessing import Process, Queue as MultiQueue
import Queue

from enum import Enum
import re
import time

from error import error

from math import *
import sympy

class calc_type(Enum):
    normal = 0
    polynomial_factorization = 1
    algebraic_equations = 2

class text_calculator(object):
    def __init__(self, timeout=15.0):
        self._queue = MultiQueue()
        self._timeout = timeout

    def calculate(self, text, debug=False, type_var=calc_type.normal):
        if text_calculator.is_non_calc(text):
            return
        
        try:
            # TODO: process dispose? (RAM Exceed)

            result_data = calc_result_data(text)
            init_time = time.time()
            # TODO: optimize process_dict (create once)
            self._process_dict = {
                calc_type.normal: Process(target=self._basic_calc_proc, args=(init_time, result_data, debug, self._queue)),
                calc_type.algebraic_equations: Process(target=self._algebraic_equations, args=(init_time, result_data, debug, self._queue)),
                calc_type.polynomial_factorization: Process(target=self._polynomial_factorization, args=(init_time, result_data, debug, self._queue))
            }
            calc_proc = self._process_dict[type_var]
            calc_proc.start()

            result_data = self._queue.get(True, self._timeout)
        except Queue.Empty:
            calc_proc.terminate()

            result_data.success = False
            result_data.calc_result = error.string_calculator.calculation_timeout(self._timeout)
                
            result_data.auto_record_time(init_time)

            if debug:
                print result_data.get_debug_text()
        except Exception as ex:
            raise ex

        return None if result_data is None else result_data

    # TODO: not used - for optimize
    def _get_calculate_proc(self, type_var, args_tuple):
        return self._process_dict.get(type_var,
                                      Process(target=self._basic_calc_proc, args=args_tuple))

    def _basic_calc_proc(self, init_time, result_data, debug, queue):
        text = result_data.formula_str
        try:
            start_time = init_time

            if 'result=' not in text:
                exec('result={}'.format(text))
            else:
                exec(text)

            result_data.auto_record_time(start_time)

            # TODO: error reported
            if isinstance(result, (float, int, long)):
                if isinstance(result, long) and result.bit_length() > 333:
                    result_data.over_length = True

                start_time = time.time()
                
                str_calc_result = unicode(result)
                if len(text_calculator.remove_non_digit(str_calc_result)) < 10:
                    print type(text)
                    print text
                    print type(str_calc_result)
                    print str_calc_result
                    print text != str_calc_result
                    if text != str_calc_result:
                        result_data.success = True
                        result_data.calc_result = str_calc_result
                else:
                    result_data.success = True
                    result_data.calc_result = str_calc_result

                result_data.auto_record_time(start_time)

            queue.put(result_data)

        except OverflowError:
            result_data.success = False
            result_data.calc_result = error.string_calculator.overflow()
                
            result_data.auto_record_time(start_time)

            if debug:
                print result_data.get_debug_text()

            queue.put(result_data)

        except Exception as ex:
            result_data.success = False
            result_data.calc_result = ex.message
                
            result_data.auto_record_time(start_time)

            if debug:
                print result_data.get_debug_text()
                queue.put(result_data)
            else:
                queue.put(None)

    def _algebraic_equations(self, init_time, result_data, debug, queue):
        pass

    def _polynomial_factorization(self, init_time, result_data, debug, queue):
        text = text_calculator.formula_to_py(result_data.formula_str)
        try:
            start_time = init_time
            exec('result = sympy.factor(text)')
            result_data.auto_record_time(start_time)

            result_data.success = True

            start_time = time.time()
            str_calc_result = str(result)
            result_data.calc_result = str_calc_result
            result_data.auto_record_time(start_time)

            queue.put(result_data)

        except Exception as ex:
            result_data.success = False
            result_data.calc_result = ex.message
                
            result_data.auto_record_time(start_time)

            if debug:
                print result_data.get_debug_text()
                queue.put(result_data)
            else:
                queue.put(None)

    @staticmethod
    def remove_non_digit(text):
        import string
        allchars = ''.join(chr(i) for i in xrange(256))
        identity = string.maketrans('', '')
        nondigits = allchars.translate(identity, string.digits)
        return text.translate(identity, nondigits)

    @staticmethod
    def is_non_calc(text):
        return (text.startswith('0') and '.' not in text) or text.startswith('+') or text.endswith('.')

    @staticmethod
    def formula_to_py(text):
        regex = ur"([\d.]*)([\d]*[\w]*)([+\-*/]?)"
        
        def add_star(match):
            if match.group(1) != '' and match.group(2) != '':
                return u'{}*{}{}'.format(match.group(1), match.group(2), match.group(3))
            else:
                return match.group()
        
        return re.sub(regex, add_star, text)

    @staticmethod
    def calculate_type(text):
        if '=' in text:
            return calc_type.algebraic_equations
        else:
            return calc_type.polynomial_factorization

class calc_result_data(object):
    def __init__(self, formula_str, calc_result=None, calc_time=-1.0, type_cast_time=-1.0, success=False):
        self._formula_str = formula_str
        self._calc_result = calc_result
        self._calc_time = calc_time
        self._type_cast_time = type_cast_time
        self._success = success
        self._over_length = False

    @property
    def formula_str(self):
        return self._formula_str
    
    @property
    def calc_result(self):
        return self._calc_result

    @calc_result.setter
    def calc_result(self, value):
        if isinstance(value, (str, unicode)):
            self._calc_result = value
        else:
            raise Exception('Calculate result should be string or unicode.')

    @property
    def calc_time(self):
        return self._calc_time

    @calc_time.setter
    def calc_time(self, value):
        self._calc_time = value
    
    @property
    def type_cast_time(self):
        return self._type_cast_time

    @type_cast_time.setter
    def type_cast_time(self, value):
        self._type_cast_time = value
    
    @property
    def success(self):
        return self._success

    @success.setter
    def success(self, value):
        self._success = value

    @property
    def over_length(self):
        return self._over_length

    @over_length.setter
    def over_length(self, value):
        self._over_length = value

    def auto_record_time(self, start_time):
        if self._calc_time == -1.0:
            self._calc_time = time.time() - start_time
        elif self._type_cast_time == -1.0:
            if self._calc_time == -1.0:
                self._calc_time = time.time() - start_time
            else:
                self._type_cast_time = time.time() - start_time

    def get_basic_text(self):
        return u'算式:\n{}\n結果:\n{}\n計算時間:\n{}\n轉型時間:\n{}'.format(
            self._formula_str,
            self._calc_result,
            u'(未執行)' if self._calc_time == -1.0 else u'{:f}秒'.format(self._calc_time),
            u'(未執行)' if self._type_cast_time == -1.0 else u'{:f}秒'.format(self._type_cast_time))

    def get_debug_text(self):
        return u'計算{}\n\n{}'.format(self.get_basic_text())

