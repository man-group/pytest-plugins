'''
Created on 25 Apr 2012

@author: eeaston

'''
import redis

from pkglib import CONFIG
from server import TestServer


class RedisTestServer(TestServer):
    """This will look for 'redis_executable' in configuration and use as the
    redis-server to run.
    """
    port_seed = 65532

    def __init__(self, db=0, **kwargs):
        self.db = db
        super(RedisTestServer, self).__init__(**kwargs)
        self.api = redis.Redis(host=self.hostname, port=self.port, db=self.db)

    @property
    def run_cmd(self):
        return [CONFIG.redis_executable, '-']

    @property
    def run_stdin(self):
        # these don't work on redis-server 2.2.12 on ubuntu precise32.
        #
        # Is it ok to just comment them out?
        #
        # zset-max-ziplist-value 64
        # zset-max-ziplist-entries 128
        cfg = ("""
        daemonize no
        port %(port)d
        bind %(hostname)s
        timeout 0
        loglevel notice
        logfile %(workspace)s/redis.log
        databases 1
        maxmemory %(maxmemory)s
        maxmemory-policy noeviction
        appendonly no
        slowlog-log-slower-than -1
        slowlog-max-len 1024
        vm-enabled no
        hash-max-zipmap-entries 512
        hash-max-zipmap-value 64
        list-max-ziplist-entries 512
        list-max-ziplist-value 64
        set-max-intset-entries 512
        activerehashing yes
        """ % {
            'port': self.port,
            'hostname': self.hostname,
            'workspace': self.workspace,
            'maxmemory': "2G",
        }).strip()
        #print "---------------\ncfg:\n%s\n---------------" % cfg
        return cfg

    def check_server_up(self):
        """ Ping the server
        """
        try:
            print "pinging Redis at %s:%s db %s" % (
                self.hostname, self.port, self.db
            )
            return redis.Redis(
                host=self.hostname,
                port=self.port,
                db=self.db
            ).ping()
        except redis.ConnectionError, e:
            print "server not up yet (%s)" % e
            return False
