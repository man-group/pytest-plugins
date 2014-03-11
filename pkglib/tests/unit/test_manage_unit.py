""" Unit tests for pkglib.manage
"""
import os

import mock

from pkglib import manage
from pkglib.config import org

pytest_plugins = ['pkglib_testing.pytest.util']


TEST_CONFIG = org.OrganisationConfig(namespaces=['acme'],
                                      namespace_separator='.')


def test_get_inhouse_dependencies(workspace):
    with mock.patch.object(manage, 'CONFIG', TEST_CONFIG):
        with open(os.path.join(workspace.workspace, 'setup.cfg'), 'wb') as fp:
            fp.write("""[metadata]
name = acme.foo
version = 2.3.5
install_requires =
    scipy
    numpy
    acme.a
    acme.b>=1.0.0
    acme.c<3.0
""")
        result = [i for i in
                  manage.get_inhouse_dependencies(workspace.workspace)]
        assert result == ['acme.a', 'acme.b', 'acme.c']
