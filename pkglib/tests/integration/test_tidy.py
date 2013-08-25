""" Unit tests for pkglib.setuptools.command.tidy
"""
import os

from pkglib.setuptools.command import tidy
from pkglib_testing.util import Workspace
from setuptools.dist import Distribution


class Test_tidy(object):

    def setup(self):
        self.tidy = tidy.tidy(Distribution())

    def test_remove_object_file(self):
        with Workspace() as w:
            fn = 'junk.txt'
            cmd = 'touch %s' % fn
            w.run(cmd)
            filepath = os.path.join(w.workspace, fn)
            assert os.path.isfile(filepath)
            self.tidy.remove_object(w.workspace, filepath)
            assert not os.path.exists(filepath)

    def test_remove_object_dir(self):
        with Workspace() as w:
            fn = 'junk'
            cmd = 'mkdir %s' % fn
            w.run(cmd)
            dirpath = os.path.join(w.workspace, fn)
            assert os.path.isdir(dirpath)
            self.tidy.remove_object(w.workspace, dirpath)
            assert not os.path.exists(dirpath)

    def test_remove_from_dir_constant_top_level(self):
        with Workspace() as w:
            fn = 'junk'
            cmd = 'mkdir %s' % fn
            w.run(cmd)
            dirpath = os.path.join(w.workspace, fn)
            assert os.path.isdir(dirpath)
            self.tidy.remove_from_dir(w.workspace, [fn])
            assert not os.path.exists(dirpath)

    def test_remove_from_dir_constant_lower_level(self):
        with Workspace() as w:
            fn = 'junk'
            cmd = 'mkdir top;cd top; mkdir %s' % fn
            w.run(cmd)
            dirpath = os.path.join(w.workspace, 'top', fn)
            assert os.path.isdir(dirpath)
            self.tidy.remove_from_dir(w.workspace, [fn])
            assert not os.path.exists(dirpath)

    def test_remove_from_file_pattern_top_level(self):
        with Workspace() as w:
            fn = 'junk.pyc'
            cmd = 'touch %s' % fn
            w.run(cmd)
            fpath = os.path.join(w.workspace, fn)
            self.tidy.remove_from_dir(w.workspace, ['*.pyc'])
            assert not os.path.exists(fpath)

    def test_remove_from_file_pattern_match_lower_level(self):
        with Workspace() as w:
            fn = 'junk.pyc'
            cmd = 'mkdir top;cd top; touch %s' % fn
            w.run(cmd)
            dirpath = os.path.join(w.workspace, 'top', fn)
            self.tidy.remove_from_dir(w.workspace, ['*.pyc'])
            assert not os.path.exists(dirpath)
