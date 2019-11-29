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
    'Topic :: Software Development :: User Interfaces',
    'Intended Audience :: Developers',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
]

install_requires = ['pytest',
                    'pytest-server-fixtures',
                    'pytest-shutil',
                    ]

tests_require = ['pytest-cov'
                 ]

entry_points = {
    'pytest11': [
        'qt = pytest_qt_app',
    ]
}

if __name__ == '__main__':
    kwargs = common_setup('pytest_qt_app')
    kwargs.update(dict(
        name='pytest-qt-app',
        description='QT app fixture for py.test',
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        tests_require=tests_require,
        py_modules=['pytest_qt_app'],
        entry_points=entry_points,
    ))
    setup(**kwargs)
