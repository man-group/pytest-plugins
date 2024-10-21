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
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3.12',
]

install_requires = ['six',
                    'pytest',
                    'gprof2dot',
                    ]

tests_require = [
                 'pytest-virtualenv',
                 ]

entry_points = {
    'pytest11': [
        'profiling = pytest_profiling',
    ]
}

if __name__ == '__main__':
    kwargs = common_setup('pytest_profiling')
    kwargs.update(dict(
        name='pytest-profiling',
        description='Profiling plugin for py.test',
        author='Ed Catmur',
        author_email='ed@catmur.co.uk',
        classifiers=classifiers,
        install_requires=install_requires,
        tests_require=tests_require,
        py_modules=['pytest_profiling'],
        entry_points=entry_points,
    ))
    setup(**kwargs)
