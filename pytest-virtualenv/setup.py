import os
from setuptools import setup

execfile(os.path.join(os.path.pardir, 'common_setup.py'))

classifiers = [
    'License :: OSI Approved :: MIT License',
    'Development Status :: 5 - Production/Stable',
    'Topic :: Software Development :: Libraries',
    'Topic :: Software Development :: Testing',
    'Topic :: Utilities',
    'Intended Audience :: Developers',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
]

install_requires = ['pytest-fixture-config',
                    'pytest-shutil',
                    'pytest',
                    ]

tests_require = ['pytest-cov',
                 'mock'
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
        tests_require=tests_require,
        py_modules=['pytest_virtualenv'],
        entry_points=entry_points,
    ))
    setup(**kwargs)
