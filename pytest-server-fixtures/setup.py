import sys
import logging

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

classifiers = [
    'License :: OSI Approved :: MIT License',
    'Development Status :: 5 - Production/Stable',
    'Topic :: Software Development :: Libraries',
    'Topic :: Software Development :: Testing',
    'Topic :: Utilities',
    'Intended Audience :: Developers',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
]

long_description = open("README.rst").read()

pytest_args = []

class PyTest(TestCommand):

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

        pytest_args.extend(['--cov', 'pytest_server_fixtures',
                     '--cov-report', 'xml',
                     '--cov-report', 'html',
                     '--junitxml', 'junit.xml',
                     ])
        errno = pytest.main(pytest_args)
        sys.exit(errno)


def main():
    # Gather trailing arguments for pytest, this can't be done using setuptools' api
    global pytest_args
    if 'test' in sys.argv:
        pytest_args = sys.argv[sys.argv.index('test') + 1:]
        if pytest_args:
            sys.argv = sys.argv[:-len(pytest_args)]

    install_requires = ['pytest',
                        'pytest-shutil',
                        'six',
                        ]

    extras_require = {
        'mongodb':  ["pymongo"],
        'jenkins':  ["python-jenkins"],
        'rethinkdb':  ["rethinkdb"],
        'redis':  ["redis"],
    }

    tests_require = ['pytest-cov',
                     'mock'
                     ]

    entry_points = {
        'pytest11': [
            'httpd_server = pytest_server_fixtures.httpd',
            'jenkins_server = pytest_server_fixtures.jenkins',
            'mongodb_server = pytest_server_fixtures.mongo',
            'redis_server = pytest_server_fixtures.redis',
            # 'rethinkdb_server = pytest_server_fixtures.mongo',
        ]
    }

    setup(
        name='pytest-server-fixtures',
        description='Extensible server fixures for py.test',
        long_description=long_description,
        version='1.0.0',
        url='https://github.com/manahl/pytest-plugins',
        license='MIT license',
        platforms=['unix', 'linux'],
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        extras_require=extras_require,
        tests_require=tests_require,
        cmdclass={'test': PyTest},
        packages=find_packages(),
        entry_points=entry_points,
    )

if __name__ == '__main__':
    main()
