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
    'Operating System :: Microsoft :: Windows',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
]

install_requires = ['six',
                    'pytest',
                    'pytest-server-fixtures'
                    ]

tests_require = []

entry_points = {
    'pytest11': [
        'listener = pytest_listener',
    ]
}

if __name__ == '__main__':
    kwargs = common_setup('pytest_listener')
    kwargs.update(dict(
        name='pytest-listener',
        description='A simple network listener',
        author='Tim Couper',
        author_email='drtimcouper@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        tests_require=tests_require,
        py_modules=['pytest_listener'],
        entry_points=entry_points,
    ))
    setup(**kwargs)
