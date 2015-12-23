from setuptools import setup, find_packages
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
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
]

install_requires = ['six',
                    'execnet',
                    'contextlib2',
                    'path.py',
                    'mock'
                    ]

tests_require = ['pytest',
                 'pytest-cov',
                 ]

entry_points = {
    'pytest11': [
        'workspace = pytest_shutil.workspace',
    ]
}

if __name__ == '__main__':
    kwargs = common_setup('pytest_shutil')
    kwargs.update(dict(
        name='pytest-shutil',
        description='A goodie-bag of unix shell and environment tools for py.test',
        author='Edward Easton',
        author_email='eeaston@gmail.com',
        classifiers=classifiers,
        install_requires=install_requires,
        tests_require=tests_require,
        packages=find_packages(exclude='tests'),
        entry_points=entry_points,
    ))
    setup(**kwargs)
