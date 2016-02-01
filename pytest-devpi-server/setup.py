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
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
]

install_requires = ['pytest-server-fixtures',
                    'pytest',
                    'devpi-server',
                    'devpi-client',
                    ]

tests_require = ['pytest-cov',
                 ]

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
        py_modules=['pytest_devpi_server'],
        entry_points=entry_points,
    ))
    setup(**kwargs)
