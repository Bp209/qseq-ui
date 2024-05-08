import time
import logging
from collections import namedtuple

from .common import frange
from .csvlog import CsvLog
from .timestamp import QSEQ_START_TIMESTAMP, QSEQ_TIMESTAMP

logger = logging.getLogger(__name__)


class ParseError(Exception):
    def __init__(self, error, lineno, line):
        Exception.__init__(self)
        self.error = error
        self.lineno = lineno
        self.line = line

    def __str__(self):
        return '%s: %s at line %d' % (self.__class__.__name__, self.error,
                                      self.lineno)


CMD_INIT = 0
CMD_FINI = 1
CMD_PERIODIC = 2
CMD_SINGLE = 3
CMD_LOAD_RESOURCES = 4
CMD_REPEAT_BEGIN = 5
CMD_REPEAT_END = 6

SequencerInputLine = namedtuple("SequencerInputLine", "cmd data")


class SequenceFileParser(object):
    def __init__(self, filename=None):
        self.filename = filename
        self.lines = list()
        self.repeat_depth = 0
        self.line = None
        self.lineno = None
        if self.filename is not None:
            self.parse_input()

    def _convert_float(self, x):
        try:
            return float(x)
        except ValueError:
            raise ParseError('Could not convert to float', self.lineno,
                             self.line)

    def _parse_line(self):
        line = self.line
        lineno = self.lineno

        # (1) remove comments
        idx = line.find('#')
        if idx >= 0:
            line = line[:idx]

        # (2) remove extra whitespaces
        line = line.strip()

        # (3) ignore empty lines
        if len(line) == 0:
            return

        if line[0] == 'R':
            cmd, line = ('R', None)
        else:
            cmd, line = line.split(None, 1)

        if cmd == 'i':
            cmd = CMD_INIT
            self.lines.append(SequencerInputLine(cmd, line))
        elif cmd == 'f':
            cmd = CMD_FINI
            self.lines.append(SequencerInputLine(cmd, line))
        elif cmd == 'p':
            cmd = CMD_PERIODIC
            delay, method = line.split(None, 1)
            delay = self._convert_float(delay)
            self.lines.append(SequencerInputLine(cmd, (delay, 0, method)))
        elif cmd == 'P':
            cmd = CMD_PERIODIC
            delay, offset, method = line.split(None, 2)
            delay = self._convert_float(delay)
            offset = self._convert_float(offset)
            if (abs(offset) >= delay):
                raise RuntimeError('offset is greater than delay for periodic'
                                   ' command')
            self.lines.append(SequencerInputLine(cmd, (delay, offset, method)))
        elif cmd == 's':
            cmd = CMD_SINGLE
            delay, method = line.split(None, 1)
            delay = self._convert_float(delay)
            self.lines.append(SequencerInputLine(cmd, (delay, method)))
        elif cmd == 'l':
            cmd = CMD_LOAD_RESOURCES
            self.lines.append(SequencerInputLine(cmd, line))
        elif cmd == 'r':
            cmd = CMD_REPEAT_BEGIN
            repeat_count = self._convert_float(line)
            self.lines.append(SequencerInputLine(cmd, repeat_count))
            self.repeat_depth += 1
        elif cmd == 'R':
            cmd = CMD_REPEAT_END
            self.lines.append(SequencerInputLine(cmd, None))
            self.repeat_depth -= 1
            if self.repeat_depth < 0:
                raise ParseError('Repeat end without begin', lineno, line)

    def parse_input(self):
        with open(self.filename) as f:
            for lineno, line in enumerate(f.readlines(), 1):
                self.line = line
                self.lineno = lineno
                self._parse_line()

        # XXX: move to parser and fix line number
        if self.repeat_depth > 0:
            raise ParseError('Repeat begin without end', -1, None)


SequenceStep = namedtuple("SequenceStep", "timestamp method")


class IsolatedEnvironment(object):
    """The class provides an isolated environment for executing python scripts.

    This is archieved by creating an own dict. This is used for every method
    call, evaluation and code compilation.
    """

    def __init__(self):
        self.globals = dict()

    def inject_global(self, name, value):
        self.globals[name] = value

    def load_script(self, filename):
        with open(filename) as f:
            script = f.read()
            code = compile(script, filename, 'exec')
            eval(code, self.globals, self.globals)

    def evaluate(self, expression):
        ret = eval(expression, self.globals, self.globals)
        if callable(ret):
            logger.warning("Returned object is callable. "
                           "Forgot function call?")
        return ret


class Sequencer(object):
    """The sequencer class parses a sequence file and executes it.

    Basically, it steps through the input file line by line. Each line consists
    of a command, which is exactly one character and data. The typical command
    is a single step, that is a method which is called exactly one time. There
    is also a periodic command, which as the name implies, is executed
    periodically. These two commands takes a time and a method. For the
    periodic command the time is the period. Before the single step is executed
    the sequencer waits the given amount of time.

    Internally, a time schedule is calculated with the periodic and single
    steps commands. First, the complete run time of all single steps are
    computed. Then, the single step commands are just inserted at the right
    timestamp and periodic commands are inserted multiple times until the
    schedule is finished, that is the complete run time is over. Once the
    schedule is computed, it is executed step by step.

    Supported commands:
     - 'l file.py' loads a python script (function definitions)
     - 'i method()' executed initialization methods at the beginning
     - 'f method()' executed finalizing methods at the end
     - 's 10 method()' single step, method() is executed after 10 seconds
     - 'p 5 method()' periodic, method() is called every 5 seconds
     - 'P 5 1 method()' periodic, method() is called every 5 seconds beginning
       with time t=1, eg. t=1, t=6, t=11, etc
    """

    def __init__(self):
        self.environment = IsolatedEnvironment()
        self.schedule = list()
        self.initializations = list()
        self.finalizations = list()
        self.resources = list()

    def _parse_input_lines(self, lines):
        # first calculate complete run time
        run_time = 0.0
        for line in lines:
            if line.cmd == CMD_SINGLE:
                run_time += line.data[0]

        # add methods, includes, etc
        ts = 0.0
        for line in lines:
            if line.cmd == CMD_INIT:
                self.initializations.append(line.data)
            elif line.cmd == CMD_FINI:
                self.finalizations.append(line.data)
            elif line.cmd == CMD_SINGLE:
                ts += line.data[0]
                self.schedule.append(SequenceStep(ts, line.data[1]))
            elif line.cmd == CMD_PERIODIC:
                for _ts in frange(line.data[1], run_time, line.data[0]):
                    _ts = _ts + line.data[0]
                    self.schedule.append(SequenceStep(_ts, line.data[2]))
            elif line.cmd in (CMD_REPEAT_BEGIN, CMD_REPEAT_END):
                raise RuntimeError('repeats not supported yet')
            elif line.cmd == CMD_LOAD_RESOURCES:
                self.resources.append(line.data)

        # sort schedule by timestamp
        self.schedule.sort(key=lambda x: x.timestamp)

        # dump parsed information
        logger.debug('Resource files:')
        for resource in self.resources:
            logger.debug('  %s', resource)

        logger.debug('Initialization methods:')
        for method in self.initializations:
            logger.debug('  %s', method)

        logger.debug('Computed schedule:')
        for step in self.schedule:
            logger.debug('  %6.2f %s', step.timestamp, step.method)

    def load_sequence_file(self, filename):
        p = SequenceFileParser(filename)
        self._parse_input_lines(p.lines)

    def _load_resources(self):
        for resource in self.resources:
            logger.debug('Loading resource %s', resource)
            self.environment.load_script(resource)

    def _eval_initializations(self):
        for method in self.initializations:
            logger.debug('Evaluating %s', method)
            self.environment.evaluate(method)

    def _eval_steps(self):
        start_time = time.time()
        for (ts, method) in self.schedule:
            delay = start_time - time.time() + ts
            if delay > 0:
                time.sleep(delay)

            logger.debug('Evaluating %s', method)

            eval_begin = time.time()
            try:
                self.environment.evaluate(method)
            except KeyboardInterrupt:
                raise
            except Exception:
                logger.exception('Exception in step %s', method)
            eval_end = time.time()

            if (eval_end - eval_begin > 1):
                logger.warning('Evaluating %s took longer than 1 second. '
                               'Consider using the DataCacheThread class.',
                               method)

    def _eval_finalizations(self):
        for method in self.finalizations:
            logger.debug('Evaluating %s', method)
            self.environment.evaluate(method)

    def start(self):
        self.environment.inject_global('qseq_start_timestamp',
                                       QSEQ_START_TIMESTAMP)
        self.environment.inject_global('qseq_timestamp', QSEQ_TIMESTAMP)
        self.environment.inject_global('qseq_log', QSEQ_LOG)

        self._load_resources()
        self._eval_initializations()
        self._eval_steps()
        self._eval_finalizations()


QSEQ_LOG = CsvLog()
