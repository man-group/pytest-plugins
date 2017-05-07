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
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
]

install_requires = ['pytest',
                    'pytest-shutil',
                    ]

tests_require = [
                 ]

entry_points = {
    'pytest11': [
        'svn_repo = pytest_svn',
    ]
}

if __name__ == '__main__':
    kwargs = common_setup('pytest_svn')
    kwargs.update(dict(
        name='pytest-svn',
        description='SVN repository fixture for py.test',
        platforms=['unix', 'linux'],
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        tests_require=tests_require,
        py_modules=['pytest_svn'],
        entry_points=entry_points,
    ))
    setup(**kwargs)
