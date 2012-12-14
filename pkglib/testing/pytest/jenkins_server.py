from pkglib.testing.jenkins_server import JenkinsTestServer


def pytest_funcarg__jenkins_server(request):
    """ Boot up Jenkins in a local thread.
        This also provides a temp workspace.
    """
    return request.cached_setup(
        setup=JenkinsTestServer,
        teardown=lambda p: p.teardown(),
        scope='session',
    )
