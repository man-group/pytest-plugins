import os
import subprocess
import time

from itertools import chain, repeat

from mock import patch
import pytest
from pytest import raises

from pytest_server_fixtures.xvfb import XvfbServer


def test_construct(xvfb_server):
        assert xvfb_server.display


def test_connect_client():
    with XvfbServer() as server:
        p = subprocess.Popen(['xdpyinfo', '-display', server.display],
                             env=dict(os.environ, XAUTHORITY=server.authfile), stdout=subprocess.PIPE)
        dpyinfo, _ = p.communicate()
        assert p.returncode == 0
        assert server.display in str(dpyinfo)


def test_terminates_on_last_client_exit():
    with XvfbServer() as server:
        subprocess.check_call(['xdpyinfo', '-display', server.display],
                              env=dict(os.environ, XAUTHORITY=server.authfile), stdout=open('/dev/null'))
        for _ in range(5):
            if server.process.poll() is not None:
                break
            time.sleep(0.1)  # wait up to 0.5 seconds for the server to terminate
        assert server.process.poll() == 0


def test_tries_to_find_free_server_num():
    with XvfbServer() as server1:
        with XvfbServer() as server2:
            assert server1.display != server2.display


def test_raises_if_fails_to_find_free_server_num():
    _exists = os.path.exists
    with patch('os.path.exists', new=lambda f: "-lock" in f or _exists(f)):
        with raises(RuntimeError) as ex:
            XvfbServer()
        assert 'Unable to find a free server number to start Xvfb' in str(ex)


def test_handles_unexpected_server_num_collision():
    with XvfbServer() as server1:
        from os.path import exists as real_exists
        with patch('os.path.exists') as mock_exists:
            side_effect_chain = chain([lambda _: False], repeat(real_exists))
            mock_exists.side_effect = lambda path: next(side_effect_chain)(path)
            with XvfbServer() as server2:
                assert server1.display != server2.display


def test_handles_unexpected_failure_to_start():
    with patch('pytest_server_fixtures.xvfb.XvfbServer.xvfb_command', '/bin/false'):
        with raises(RuntimeError) as ex:
            XvfbServer()
        assert 'Failed to start Xvfb' in str(ex)
