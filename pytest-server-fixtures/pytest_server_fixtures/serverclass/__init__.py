"""
Implementation of how a server fixture will run.
"""
# flake8: noqa
from __future__ import absolute_import

def create_server(server_class, **kwargs):
    if server_class == 'thread':
        from .thread import ThreadServer
        return ThreadServer(
            kwargs["get_cmd"],
            kwargs["env"],
            kwargs["workspace"],
            cwd=kwargs["cwd"],
            random_hostname=kwargs["random_hostname"],
        )

    if server_class == 'docker':
        from .docker import DockerServer
        return DockerServer(
            kwargs["server_type"],
            kwargs["get_cmd"],
            kwargs["env"],
            kwargs["image"],
        )

    if server_class == 'kubernetes':
        from .kubernetes import KubernetesServer
        return KubernetesServer(
            kwargs["server_type"],
            kwargs["get_cmd"],
            kwargs["env"],
            kwargs["image"],
        )
