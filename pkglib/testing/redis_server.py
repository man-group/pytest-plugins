'''
Created on 25 Apr 2012

@author: eeaston
'''
import redis

from server import TestServer


class RedisTestServer(TestServer):
    port_seed = 65532

    def __init__(self, db=0, **kwargs):
        self.db = db
        super(RedisTestServer, self).__init__(**kwargs)
        self.api = redis.Redis(host=self.hostname, port=self.port, db=self.db)

    @property
    def run_cmd(self):
        return ['/usr/sbin/redis-server', '-']

    @property
    def run_stdin(self):
        return """
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
        zset-max-ziplist-entries 128
        zset-max-ziplist-value 64
        activerehashing yes
        """ % {
       'port': self.port,
       'hostname': self.hostname,
       'workspace': self.workspace,
       'maxmemory': "2G",
        }

    def check_server_up(self):
        """ Ping the server
        """
        try:
            print "pinging Redis at %s:%s db %s" % (self.hostname, self.port, self.db)
            return redis.Redis(host=self.hostname, port=self.port, db=self.db).ping()
        except redis.ConnectionError, e:
            print "server not up yet (%s)" % e
            return False
