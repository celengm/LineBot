# -*- coding: utf-8 -*-
from enum import Enum
from error import error
from math import *
import sympy
import time
from multiprocessing import Process, Queue as MultiQueue
import Queue

class text_calculator(object):
    def __init__(self, timeout=15.0):
        self._queue = MultiQueue()
        self._timeout = timeout

    def basic_calc(self, text, debug=False):
        if text_calculator.is_non_calc(text):
            return
        
        result_data = calc_result_data(text)
        try:
            calc_proc = Process(target=self._exec_calc, args=(result_data, debug, self._queue))

            calc_proc.start()
            calc_proc.join()
            print 'MAIN'
            result_data = self._queue.get(True, self._timeout)
            print 'MAIN COMPLETE'
        except Queue.Empty:
            print 'MAIN TIMEOUT'
            result_data.success = False
            result_data.calc_result = error.string_calculator.calculation_timeout(self._timeout, text)
                
            result_data.auto_record_time(start_time)

            if debug:
                print result_data.get_debug_text()

        print result_data is None
        if result_data is not None:
            print result_data.get_basic_text().encode('utf-8')
        return None if result_data is None else result_data

    def _exec_calc(self, result_data, debug, queue):
        text = result_data.formula_str
        try:
            start_time = time.time()

            if 'result=' not in text:
                exec('result={}'.format(text))
            else:
                exec(text)

            result_data.auto_record_time(start_time)

            if isinstance(result, (float, int, long)):
                result_data.success = True

                if isinstance(result, long) and result.bit_length() > 333:
                    result_data.over_length = True

                start_time = time.time()
                
                str_calc_result = str(result)
                if len(text_calculator.remove_non_digit(str_calc_result)) < 10:
                    if text != str_calc_result:
                        result_data.calc_result = str_calc_result
                else:
                    result_data.calc_result = str_calc_result

                result_data.auto_record_time(start_time)
            else:
                result_data.success = False

            queue.put(result_data)

        except OverflowError:
            result_data.success = False
            result_data.calc_result = error.string_calculator.overflow(text)
                
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

    @staticmethod
    def _polynomial_factorication(text):
        pass

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
        regex = ur"([\d.]*)([\d]*[\w]*)([+\-*/]{1})"
        
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

class calc_type(Enum):
    unknown = 0
    polynomial_factorization = 1
    algebraic_equations = 2

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
        self._calc_result = value

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
        return u'算式:\n{}\n結果:\n{}\n計算時間:\n{}秒\n轉型時間:\n{}秒'.format(
            self._formula_str,
            self._calc_result,
            u'(未執行)' if self._calc_time == -1.0 else self._calc_time,
            u'(未執行)' if self._type_cast_time == -1.0 else self._type_cast_time)

    def get_debug_text(self):
        return u'計算{}\n\n{}'.format(self.get_basic_text())

