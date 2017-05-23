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
    'Framework :: Pyramid',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
]


install_requires = ['pytest-server-fixtures',
                    'pytest',
                    'pyramid',
                    'waitress',
                    'six',
                    ]

tests_require = [
                 'pyramid-debugtoolbar',
                 ]

entry_points = {
    'pytest11': [
        'pyramid_server = pytest_pyramid_server',
    ],
    'paste.app_factory': [
        'pyramid_server_test = pyramid_server_test:main',
    ],
}

if __name__ == '__main__':
    kwargs = common_setup('pytest_pyramid_server')
    kwargs.update(dict(
        name='pytest-pyramid-server',
        description='Pyramid server fixture for py.test',
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        tests_require=tests_require,
        py_modules=['pytest_pyramid_server', 'pyramid_server_test'],
        entry_points=entry_points,
    ))
    setup(**kwargs)
