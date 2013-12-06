#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用来作为接受google统计上报的server端
通过zmq通道
"""

import os
import sys
import time
from optparse import OptionParser
import os.path as op
import pickle
import functools
import logging
import logging.config

import zmq

logger = logging.getLogger('default')

DEV_ENV = 'DEV_ENV' in os.environ and os.environ['DEV_ENV'] == '1'

# 日志
# 为了保证邮件只有在正式环境发送
class RequireDebugOrNot(logging.Filter):
    _need_debug = False

    def __init__(self, need_debug, *args, **kwargs):
        super(RequireDebugOrNot, self).__init__(*args, **kwargs)
        self._need_debug = need_debug
        
    def filter(self, record):
        return DEV_ENV if self._need_debug else not DEV_ENV


FILE_MODULE_NAME = op.splitext(op.basename(__file__))[0]

MONITORS = ['xmonitor@qq.com']

LOG_FILE_PATH = op.abspath(op.join(op.dirname(__file__), "%s.log" % FILE_MODULE_NAME))

LOG_FORMAT = '\n'.join((
    '/' + '-' * 80,
    '[%(levelname)s][%(asctime)s][%(process)d:%(thread)d][%(filename)s:%(lineno)d %(funcName)s]:',
    '%(message)s',
    '-' * 80 + '/',
))

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,

    'formatters': {
        'standard': {
            'format': LOG_FORMAT,
        },
    },

    'filters': {
        'require_debug_false': {
            '()': RequireDebugOrNot,
            'need_debug': False,
        },
        'require_debug_true': {
            '()': RequireDebugOrNot,
            'need_debug': True,
        },
    },

    'handlers': {
        'mail': {
            'level': 'CRITICAL',
            'class': 'logging.handlers.SMTPHandler',
            'formatter': 'standard',
            'filters': ['require_debug_false'],
            'mailhost': 'smtp.qq.com',
            'fromaddr': 'xmonitor@qq.com',
            'toaddrs': MONITORS,
            'subject': '[supervisor-%s]Attention!' % FILE_MODULE_NAME,
            'credentials': ('xmonitor', 'xmr2013'),
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'filters': ['require_debug_true'],
            'filename': LOG_FILE_PATH,
        },
    },

    'loggers': {
        'default': {
            'handlers': ['file', 'mail'],
            'level': 'DEBUG',
            'propagate': False
        },
    }
}

EVENT_TYPES = (
)


def record_exception(func):
    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            logger.fatal('exception occur. msg[%s], traceback[%s]', str(e), __import__('traceback').format_exc())
            return None

    return func_wrapper


@record_exception
def handle_message(message):
    data = pickle.loads(message)

    return getattr(data['caller'], data['funcname'])(*data['args'], **data['kwargs'])


class GAServer(object):
    _port = None

    def __init__(self, port):
        self._port = port

    def run(self):
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind("tcp://*:%s" % self._port)

        while True:
            message = socket.recv()

            handle_message(message)

 
def build_parser():
    parser = OptionParser(usage="Usage: %prog [options]")
    parser.add_option("-p", "--port", dest="port", help="bind port", action="store")
    return parser


def configure_logging():
    logging.config.dictConfig(LOGGING)

 
def main():
    configure_logging()

    parser = build_parser()
    options, system = parser.parse_args()
 
    logger.info('DEV_ENV:%s, port: %s', DEV_ENV, options.port)

    prog = GAServer(options.port)
    prog.run()
 
if __name__ == '__main__':
    main()
