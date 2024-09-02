# Common setup.py code shared between all the projects in this repository
import sys
import os
import logging

from setuptools.command.test import test as TestCommand
from wheel.bdist_wheel import bdist_wheel


class PyTest(TestCommand):
    pytest_args = []
    src_dir = None

    def initialize_options(self):
        TestCommand.initialize_options(self)

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(message)s', level='DEBUG')
        # import here, cause outside the eggs aren't loaded
        import pytest
        self.pytest_args.extend(['--junitxml', 'junit.xml'])
        logger = logging.getLogger(__name__)
        logger.info("Pytest args are {}".format(str(PyTest.pytest_args)))
        errno = pytest.main(PyTest.pytest_args)
        sys.exit(errno)


def common_setup(src_dir):
    this_dir = os.path.dirname(__file__)
    readme_file = os.path.join(this_dir, 'README.md')
    changelog_file = os.path.join(this_dir, 'CHANGES.md')
    version_file = os.path.join(this_dir, 'VERSION')

    # Convert Markdown to RST for PyPI
    try:
        import pypandoc
        long_description = pypandoc.convert_file(readme_file, 'rst')
        changelog = pypandoc.convert_file(changelog_file, 'rst')
    except (IOError, ImportError, OSError):
        with open(readme_file) as f:
            long_description = f.read()
        with open(changelog_file) as f:
            changelog = f.read()

    # Gather trailing arguments for pytest, this can't be done using setuptools' api
    if 'test' in sys.argv:
        PyTest.pytest_args = sys.argv[sys.argv.index('test') + 1:]
        if PyTest.pytest_args:
            sys.argv = sys.argv[:-len(PyTest.pytest_args)]
    PyTest.src_dir = src_dir

    return dict(
            # Version is shared between all the projects in this repo
            version=open(version_file).read().strip(),
            long_description='\n'.join((long_description, changelog)),
            url='https://github.com/man-group/pytest-plugins',
            license='MIT license',
            platforms=['unix', 'linux'],
            cmdclass={'test': PyTest, 'bdist_wheel': bdist_wheel},
            include_package_data=True
            )
