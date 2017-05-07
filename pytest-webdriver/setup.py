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
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
]

install_requires = ['py',
                    'pytest',
                    'pytest-fixture-config',
                    'selenium',
                    ]

tests_require = [
                 ]

entry_points = {
    'pytest11': [
        'webdriver = pytest_webdriver',
    ]
}

if __name__ == '__main__':
    kwargs = common_setup('pytest_webdriver')
    kwargs.update(dict(
        name='pytest-webdriver',
        description='Selenium webdriver fixture for py.test',
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        tests_require=tests_require,
        py_modules=['pytest_webdriver'],
        entry_points=entry_points,
    ))
    setup(**kwargs)
