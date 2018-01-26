import collections
import json
import logging
import socket
import time
from threading import Thread, Event
from time import sleep

import pytest
from six import string_types
from six.moves import cPickle
from pytest_server_fixtures.base import get_ephemeral_port, get_ephemeral_host

TERMINATOR = json.dumps(['STOP']).encode('utf-8')
CLEAR = json.dumps(['CLEAR']).encode('utf-8')
TIMEOUT_DEFAULT = 10
DEBUG = False
logger = logging.getLogger('pytest-listener')


@pytest.yield_fixture(scope='module')
def listener(request):
    """ Simple module-scoped network listener. 
    
    Methods
    -------
    send(data, timeout):  Send data to the listener
    recieve(timeout):     Recieve data from the listener
    clear_queue():        Clear the listener queue
    """
    res = Listener()
    res.start()
    # Wait for socket to become available
    time.sleep(1)
    yield res
    stop_listener(res)


def stop_listener(listener):
    # the listener is most likely to be blocked on waiting for an accept,
    # so send it the STOP message:
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect((listener.host, listener.port))
        s.send(TERMINATOR)
    except socket.error:
        s.close()


class TimedMsg(object):
    def __init__(self, value):
        self.value = value
        self.time = time.time()

    def __str__(self):
        return 'TimedMsg: %s (@ %s)' % (str(self.value), self.time)

    def pickled(self):
        return cPickle.dumps(self)


class Listener(Thread):

    def __init__(self, host=None):
        super(Listener, self).__init__()
        self.host = host or get_ephemeral_host()
        self.port = get_ephemeral_port(host=self.host)
        self._stop_event = Event()
        self.clear_time = None

        self.s = socket.socket()
        self.queue = collections.deque()
        self.s.bind((self.host, self.port))

    def run(self):
        if DEBUG:
            logger.info('listening on %s:%s' % (self.host, self.port))
        self.s.listen(5)
        while True:
            if self.stopped:
                return
            c, addr = self.s.accept()
            if DEBUG:
                logger.info('got connection %s' % str(addr))
            data = c.recv(1024)
            if DEBUG:
                logger.info('got data: %s' % str(data))
            if data == TERMINATOR:
                self.stop()
                return
            elif data == CLEAR:
                if DEBUG:
                    logger.info('clearing')
                self.clear_time = time.time()
            else:
                self.queue.appendleft(data)
            c.close()

    def put_data(self, data):
        s = socket.socket()
        s.connect((self.host, self.port))
        s.send(data)
        s.close()

    def get_data(self):
        """ pops the latest off the queue, or None is there is none
        """
        try:
            data = self.queue.pop()
        except IndexError:
            return None, None

        try:
            data = cPickle.loads(data)
        except:
            try:
                data = data.decode('utf-8')
            except:
                pass

        if DEBUG:
            logger.info('got %s' % str(data))

        t = None
        if isinstance(data, TimedMsg):
            d = data.value
            t = data.time
        elif isinstance(data, string_types):
            try:
                d = json.loads(data)
            except:
                d = data
        else:
            d = data

        return d, t

    def _process_chunk(self, d, t):
        if t is not None:
            if DEBUG:
                logger.info('diff %s' % (t - self.clear_time))
            if t < self.clear_time:
                if DEBUG:
                    logger.info('%s < %s' % (t, self.clear_time))
                    logger.info('discarding cleared %s' % d)
                return True
            else:
                if DEBUG:
                    logger.info('removed clearing')
                self.clear_time = None  # unset as we've got one after last clear
        else:
            if DEBUG:
                logger.info('removed clearing (nmsg with no time)')
            self.clear_time = None

        return False

    def receive(self, timeout=TIMEOUT_DEFAULT):
        if timeout is not None:
            MAX_COUNT = int(timeout) * 10
        d = None
        count = 0
        while d is None and count < MAX_COUNT:

            d, t = self.get_data()
            if d is None:
                sleep(.1)
                if timeout is not None:
                    count += 1
            elif self.clear_time is not None and self._process_chunk(d, t):
                count = 0
                d = None

        return d

    def send(self, data, timeout=TIMEOUT_DEFAULT):  # @UnusedVariable
        payload = TimedMsg(data).pickled()
        if DEBUG:
            logger.info('sending %s' % str(data))
        self.put_data(payload)

    def clear_queue(self):
        self.put_data(CLEAR)
        time.sleep(.05)

    def stop(self):
        try:
            self.s.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        self.s.close()
        self._stop_event.set()

    @property
    def stopped(self):
        return self._stop_event.isSet()


if __name__ == '__main__':
    import sys
    DEBUG = True
    listener = Listener('localhost')

    listener.start()
    while not listener.stopped:
        try:
            sleep(.1)
        except KeyboardInterrupt:
            sys.exit(1)
