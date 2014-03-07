from __future__ import absolute_import

import os
import sys

from setuptools import setup as setuptools_setup, find_packages

from pkglib import config, util
from pkglib.setuptools.command import (develop, test, jenkins, egg_info, easy_install,
                                       pyinstall, update, pyuninstall, build_sphinx,
                                       build_ext, upload, register, upload_docs,
                                       depgraph, clean, test_egg, deploy,
                                       build_ext_static_interpreter, ext_gcov_test,
                                       sanity_check)

from .dist import Distribution


DEFAULT_CMD_CLASS = util.ReadOnlyDict({
    'develop': develop.develop,
    'easy_install': easy_install.easy_install,
    'egg_info': egg_info.egg_info,
    'jenkins': jenkins.jenkins,
    'update': update.update,
    'depgraph': depgraph.depgraph,
    'pyinstall': pyinstall.pyinstall,
    'build_sphinx': build_sphinx.build_sphinx,
    'build_ext': build_ext.build_ext,
    'build_ext_static_interpreter': (build_ext_static_interpreter
                                     .build_ext_static_interpreter),
    'ext_gcov_test': ext_gcov_test.ext_gcov_test,
    'test_egg': test_egg.test_egg,
    'upload': upload.upload,
    'deploy': deploy.deploy,
    'register': register.register,
    'upload_docs': upload_docs.upload_docs,
    'clean': clean.clean,
    'uninstall': pyuninstall.pyuninstall,
    'test': test.test,
    'sanity_check': sanity_check.sanity_check,
})
ALIASES = util.ReadOnlyDict({
    'tidy': 'clean --tidy',
    'cleanup': 'clean --site-packages',
    'remove': 'uninstall',
    'nosetests': 'test',
    'pytest': 'test',
})


def set_working_dir():
    """ Make sure we're working in the right directory, and ensure this is
        actually a setup.py file.
    """
    setup_py = sys.argv[0]
    if os.path.basename(setup_py) != 'setup.py':
        sys.stderr.write("You should only only be running this as "
                         "'python path/to/setup.py'")
        sys.exit(1)

    setup_py_dir = os.path.dirname(setup_py)
    if setup_py_dir:
        os.chdir(setup_py_dir)


def check_multiple_call(called=[]):
    if called:
        sys.stderr.write("setup() has already been run! setup.py should only "
                         "call setup() once.\n")
        sys.exit(1)
    called.append(True)


def check_distclass(distclass):
    if issubclass(distclass, Distribution):
        return

    sys.stderr.write("Distribution class must be a subclass of "
                     "`ahl.pkgtutils.setuptools.Distribution`, but got: %s\n"
                     % str(distclass))
    sys.exit(1)


def setup(**kwargs):
    """
    Call the regular `setuptools.setup` function with data read from
    our setup.cfg file.

    Parameters
    ----------
    kwargs : arguments dictionary
        Override any of the default `setuptools.setup` keyword arguments.

    """
    check_multiple_call()
    original_cwd = os.getcwd()
    set_working_dir()
    # Base set of defaults
    call_args = dict(
        distclass=Distribution,
        name='',
        version='',
        description='',
        long_description='',
        keywords='',
        author='',
        author_email='',
        url='',
        setup_requires=[],
        install_requires=[],
        tests_require=[],
        license='Proprietary',
        classifiers=[],
        entry_points={},
        scripts=[],
        ext_modules=[],
        packages=find_packages(exclude=['test*']),
        include_package_data=True,
        zip_safe=True,
        namespace_packages=[],
        original_cwd=original_cwd,
        cmdclass=dict(DEFAULT_CMD_CLASS),
        options=dict(
             aliases=dict(ALIASES),
        ))

    # Get the package metadata from the setup.cfg file
    call_args.update(config.parse_pkg_metadata(config.get_pkg_cfg_parser()))

    # Overrides/updates attributes from call arguments.
    # Override for scalar, update for dictionaries.
    for k, v in kwargs.items():
        if type(v) is dict and k in call_args:
            call_args[k].update(v)
        else:
            call_args[k] = v

    check_distclass(call_args["distclass"])

    # Call base setup method, retrieve distribution
    dist = setuptools_setup(**call_args)

    # Check if we've set a failed flag this may be due to a failed upload.
    if hasattr(dist, '_failed') and dist._failed:
        raise SystemExit(1)
