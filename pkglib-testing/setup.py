import os, sys
from setuptools import setup, Command


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


class PyTest(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        import sys, subprocess, pytest
        PPATH = [x for x in os.environ.get("PYTHONPATH", "").split(":") if x]
        PPATH.insert(0, os.getcwd())
        os.environ["PYTHONPATH"] = ":".join(PPATH)
        errno = subprocess.call([sys.executable, pytest.__file__, 'tests', '--cov=pkglib_testing'])
        raise SystemExit(errno)


def main():
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
        version='0.10.0',
        # url='',
        license='MIT license',
        platforms=['unix', 'linux'],
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        cmdclass={'test': PyTest},
    )

if __name__ == '__main__':
    main()
