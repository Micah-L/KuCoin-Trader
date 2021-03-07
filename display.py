# Copyright 2021 Micah Loverro
# Loverro Software Consulting
# Permission is hereby granted, to any person obtaining a copy of this software and associated documentation files (the "Software"),
# to use or copy this software. Permission is not granted to publish, distribute, sublicense, and/or sell copies of the Software.
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF 
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHOR OR COPYRIGHT HOLDER BE LIABLE 
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION 
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. THE AUTHOR OR COPYRIGHT HOLDERS SHALL NOT BE RESPONSIBLE FOR ANY LOSS 
# OF PROPERTY OR ASSETS FROM USING THIS SOFTWARE.


from collections import deque
import time
from dateutil.parser import parse as parse_time
from typing import Callable

import logging


def get_age_of_time(t):
    return time.time() - time.mktime(parse_time(t).timetuple())

class Display:
    def __init__(self, *lines: str, num_lines: int = None, width: int = None, callback: Callable = lambda x: None, priority: float = 0):
        self.priority = priority
        self.num_lines = num_lines
        self.logger = None
        self.lines = deque(maxlen=self.num_lines)
        self.callback = callback
        self.feedlines(*lines)


    def __str__(self):
        try:
            return '\n'.join(self.lines) 
        except TypeError:
            raise Exception(self.lines)
    def log(self, line: str):
        self.callback(line)
        if self.logger is not None:
            self.logger.info(line)

    def feedlines(self, *lines: str):
        for line in lines:
            self.lines.append(line)
            self.log(line)

    def setlines(self, *lines: str):
        self.lines = deque(lines, maxlen=self.num_lines)
        for line in lines:
            self.log(line)

    def clear(self):
        self.lines = deque(maxlen=self.num_lines)

    def set_logger(self, logger_name: str): 
        self.logger = logging.getLogger(logger_name)



class TimedDisplay(Display):
    """ Entries are automatically timestamped and deleted after a set time. """
    def __init__(self, *args, disappear_time: float = float('Inf'), time_format: str = '%X', **kwargs):
        self.time_format = time_format
        self.disappear_time = disappear_time
        self.logger = None
        super().__init__(*args, **kwargs)
    def __str__(self):
        self.rm_old_lines()
        return super().__str__()
    def feedlines(self, *lines: str):
        self.rm_old_lines()
        super().feedlines(*[f"[{time.strftime(self.time_format)}] {l}" for l in lines])
    def rm_old_lines(self):
        self.lines = deque( filter(lambda l: get_age_of_time(l.split(']')[0][1:]) < self.disappear_time, self.lines), maxlen=self.num_lines) 

class ConsoleInterface:
    """ Formats its own data and nicely displays them to console """
    def __str__(self):
        return '\n'.join([str(disp) for disp in self.displays])

    def __init__(self, *displays):
        self.displays = list(displays)
    def add(self, display):
        self.displays.append(display)

class CombinedDisplay(ConsoleInterface):
    """ Allows some entries to fade and some to stay by combining multiple timed displays. Sorts entries before printing.
    If max_lines is set, and the number of lines in all displays is greater, lines from lower priority displays are ignored first."""
    def __init__(self, *displays, max_lines: int = None):
        self.max_lines = max_lines
        super().__init__(*displays)
    def __str__(self):
        if self.max_lines is None:
            lines = sorted( super().__str__().split('\n') )
        else:
            lines = []
            for disp in sorted(self.displays,key = lambda d: d.priority):
                lines += str(disp).split('\n')
            lines = sorted(lines[-1*self.max_lines:])
        return '\n'.join(lines)

if __name__ == "__main__":
    d = Display("line", "line2", callback=lambda x: print(f"Callback {x}"))
    # print(d.lines)
    d.set_logger('my_logger')
    d.log('hi')