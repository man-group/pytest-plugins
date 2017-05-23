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
    'Framework :: Pyramid',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
]

install_requires = ['pytest-server-fixtures',
                    'pytest',
                    'devpi-server>=3.0.1',
                    'devpi-client',
                    'six',
                    ]

tests_require = []

entry_points = {
    'pytest11': [
        'devpi_server = pytest_devpi_server',
    ],
}

if __name__ == '__main__':
    kwargs = common_setup('pytest_devpi_server')
    kwargs.update(dict(
        name='pytest-devpi-server',
        description='DevPI server fixture for py.test',
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        tests_require=tests_require,
        packages=find_packages(exclude='tests'),
        entry_points=entry_points,
    ))
    setup(**kwargs)
