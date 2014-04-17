from __future__ import absolute_import

import os
import sys

import pytest
from mock import patch

from pkglib.scripts import pyinstall
from zc.buildout.easy_install import _get_index


def test_pyinstall_respects_i_flag():
    """Ensure that pyinstall allows us to override the PyPI URL with -i,
    even if it's already set in the config.

    """
    pypi_url = "http://some-pypi-host/simple"
    package_name = "some-package"
    expected_url = "%s/%s/" % (pypi_url, package_name)

    class OpenedCorrectUrl(Exception):
        pass

    def fake_urlopen(request, *args, **kwargs):
        assert request.get_full_url() == expected_url

        # We don't actually want pyinstall to install anything, so we
        # raise an exception so we terminate here.
        raise OpenedCorrectUrl()

    def get_index(*args, **kwargs):
        index = _get_index(*args, **kwargs)
        index.opener = fake_urlopen
        return index

    with patch('zc.buildout.easy_install._get_index', get_index):
        # Call pyinstall with the -i flag.
        args = ['pyinstall', '-i', pypi_url, package_name]
        with patch.object(sys, 'argv', args):
            try:
                pyinstall.main()
            except OpenedCorrectUrl:
                pass
