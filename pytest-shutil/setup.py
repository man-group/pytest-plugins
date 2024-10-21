import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from setuptools import setup, find_packages
from common_setup import common_setup

classifiers = [
    'License :: OSI Approved :: MIT License',
    'Development Status :: 5 - Production/Stable',
    'Topic :: Software Development :: Libraries',
    'Topic :: Software Development :: Testing',
    'Topic :: Utilities',
    'Intended Audience :: Developers',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
]

install_requires = [
    'six',
    'execnet',
    'pytest',
    'termcolor',
    'importlib_metadata;python_version<"3.8"',
]

tests_require = ['pytest',
                 ]

entry_points = {
    'pytest11': [
        'workspace = pytest_shutil.workspace',
    ]
}

if __name__ == '__main__':
    kwargs = common_setup('pytest_shutil')
    kwargs.update(dict(
        name='pytest-shutil',
        description='A goodie-bag of unix shell and environment tools for py.test',
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        tests_require=tests_require,
        packages=find_packages(exclude='tests'),
        entry_points=entry_points,
    ))
    setup(**kwargs)
