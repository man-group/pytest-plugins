import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from setuptools import setup
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

install_requires = ['pytest-fixture-config',
                    'pytest-shutil',
                    'pytest',
                    'virtualenv',
                    'importlib-metadata',
                    ]

entry_points = {
    'pytest11': [
        'virtualenv = pytest_virtualenv',
    ]
}

if __name__ == '__main__':
    kwargs = common_setup('pytest_virtualenv')
    kwargs.update(dict(
        name='pytest-virtualenv',
        description='Virtualenv fixture for py.test',
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        py_modules=['pytest_virtualenv'],
        entry_points=entry_points,
    ))
    setup(**kwargs)
