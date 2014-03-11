import sys
import os
from setuptools import setup, Command, find_packages


classifiers = [
    'License :: OSI Approved :: MIT License',
    'Development Status :: 4 - Beta',
    'Topic :: Software Development :: Libraries',
    'Topic :: Software Development :: Testing',
    'Topic :: Database',
    'Topic :: Utilities',
    'Framework :: Pyramid'
    'Intended Audience :: Developers',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
]

long_description = open("README.rst").read()

trailing_args = []


class Test(Command):
    user_options = [('unit', None, 'Just run unit tests'),
                    ('integration', None, 'Just run integration tests'),
                    ]
    boolean_options = ['unit', 'integration']

    def initialize_options(self):
        self.unit = False
        self.integration = False

    def finalize_options(self):
        pass

    def run(self):
        import subprocess
        import pytest

        tests = []
        if not (self.unit or self.integration):
            tests = ['tests']
        if self.unit:
            tests.append(os.path.join('tests', 'unit'))
        if self.integration:
            tests.append(os.path.join('tests', 'integration'))
        errno = subprocess.call([sys.executable, pytest.__file__] + tests + trailing_args)
        raise SystemExit(errno)


def main():
    # Gather trailing arguments for pytest, this can't be done using setuptools' api
    global trailing_args
    if 'test' in sys.argv:
        test_args = sys.argv[sys.argv.index('test') + 1:]
        for idx, arg in enumerate(test_args):
            if arg not in ('--unit', '--integration'):
                trailing_args = test_args[idx:]
                sys.argv = sys.argv[:-len(trailing_args)]
                break

    # TODO: split these up into optional deps
    install_requires = ['six',
                        'pytest',
                        'pytest-cov',
                        'mock',
                        'contextlib2',
                        'execnet',
                        'redis',
                        'selenium',
                        'pymongo',
                        'SQLAlchemy',
                        'path.py',
                        'python-jenkins',
                        ]
    setup(
        name='pkglib-testing',
        description='PkgLib testing library',
        long_description=long_description,
        version='0.10.1',
        # url='',
        license='MIT license',
        platforms=['unix', 'linux'],
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        cmdclass={'test': Test},
        packages=find_packages(),
    )

if __name__ == '__main__':
    main()
