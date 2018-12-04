"""
Implementation of how a server fixture will run.
"""
# flake8: noqa
from __future__ import absolute_import

from pytest_server_fixtures import CONFIG

if CONFIG.server_class == 'thread':
    from .thread import ThreadServer
if CONFIG.server_class == 'docker':
    from .docker import DockerServer
if CONFIG.server_class == 'kubernetes':
    from .kubernetes import KubernetesServer
