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
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
]

install_requires = ['pytest',
                    'six',
                    ]

tests_require = ['mock; python_version<"3.3"',
                 'pytest-virtualenv',
                 'coverage',
                 ]

entry_points = {
    'pytest11': [
        'verbose-parametrize = pytest_verbose_parametrize',
    ]
}

if __name__ == '__main__':
    kwargs = common_setup('pytest_verbose_parametrize')
    kwargs.update(dict(
        name='pytest-verbose-parametrize',
        description='More descriptive output for parametrized py.test tests',
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        tests_require=tests_require,
        py_modules=['pytest_verbose_parametrize'],
        entry_points=entry_points,
    ))
    setup(**kwargs)
