import os, sys
from setuptools import setup, Command, find_packages


classifiers = [
    'License :: OSI Approved :: MIT License',
    'Development Status :: 4 - Beta',
    'Topic :: Software Development :: Libraries',
    'Topic :: Utilities',
    'Intended Audience :: Developers',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
]

long_description = "PkgLib utilities package"


class PyTest(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        import sys, subprocess, pytest
        errno = subprocess.call([sys.executable, pytest.__file__, 'tests'])
        raise SystemExit(errno)


def main():
    setup(
        name='pkglib-util',
        description='PkgLib Utility Library',
        long_description=long_description,
        version='0.10.0',
        # url='',
        license='MIT license',
        platforms=['unix', 'linux'],
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=[],
        tests_require=['pytest'],
        packages=find_packages(),
        cmdclass={'test': PyTest},
    )

if __name__ == '__main__':
    main()
