import os
from setuptools import setup, find_packages

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

install_requires = ['pytest',
                    'pytest-shutil',
                    'pytest-fixture-config',
                    'six',
                    'requests',
                    ]

extras_require = {
    'mongodb':  ["pymongo"],
    'jenkins':  ["python-jenkins"],
    'rethinkdb':  ["rethinkdb"],
    'redis':  ["redis"],
}

tests_require = ['pytest-cov',
                 'mock',
                 'psutil',
                 ]

entry_points = {
    'pytest11': [
        'httpd_server = pytest_server_fixtures.httpd',
        'jenkins_server = pytest_server_fixtures.jenkins',
        'mongodb_server = pytest_server_fixtures.mongo',
        'redis_server = pytest_server_fixtures.redis',
        'rethinkdb_server = pytest_server_fixtures.rethink',
        'xvfb_server = pytest_server_fixtures.xvfb',
    ]
}

if __name__ == '__main__':
    kwargs = common_setup('pytest_server_fixtures')
    kwargs.update(dict(
        name='pytest-server-fixtures',
        description='Extensible server fixures for py.test',
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        extras_require=extras_require,
        tests_require=tests_require,
        packages=find_packages(exclude='tests'),
        entry_points=entry_points,
    ))
    setup(**kwargs)
