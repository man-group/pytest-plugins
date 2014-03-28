import sys

import pytest
from mock import patch

from pkglib.scripts import pyinstall


@pytest.mark.xfail
def test_pyinstall_respects_i_flag():
    """Ensure that pyinstall allows us to override the PyPI URL with -i,
    even if it's already set in the config.

    """
    pypi_url = "http://some-pypi-host/simple"
    package_name = "some-package"
    expected_url = "%s/%s/" % (pypi_url, package_name)

    class OpenedCorrectUrl(Exception): pass

    def fake_urlopen(request, *args, **kwargs):
        assert request.get_full_url() == expected_url

        # We don't actually want pyinstall to install anything, so we
        # raise an exception so we terminate here.
        raise OpenedCorrectUrl()

    with patch('urllib2.urlopen', fake_urlopen):

        # Call pyinstall with the -i flag.
        args = ['pyinstall', '-i', pypi_url, package_name]
        with patch.object(sys, 'argv', args):

            try:
                pyinstall.main()
            except OpenedCorrectUrl:
                pass
