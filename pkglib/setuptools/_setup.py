import os
import sys

from distutils import log
from setuptools import setup as _setup, find_packages, dist as _dist

from pkglib import config, CONFIG
from pkglib.manage import get_pkg_description, get_namespace_packages

from pkglib.setuptools.command import (
    develop, test, jenkins, egg_info, pyinstall, update, pyuninstall,
    build_sphinx, build_ext, upload, register, upload_docs, deploy, depgraph,
    cleanup, tidy, test_egg, release_externals, build_ext_static_interpreter,
    ext_gcov_test, config as config_cmd)


def set_working_dir():
    """ Make sure we're working in the right directory, and ensure this is
        actually a setup.py file.
    """
    setup_py = sys.argv[0]
    if os.path.basename(setup_py) == 'setup.py':
        setup_py_dir = os.path.dirname(setup_py)
        if setup_py_dir:
            os.chdir(setup_py_dir)
    if not os.path.isfile(os.path.join(os.getcwd(), 'setup.cfg')):
        log.fatal("Can't find setup.cfg")


def clean_requires(reqs):
    """Removes requirements that aren't needed in newer python versions."""
    if sys.version_info[:2] < (2, 7):
        return reqs
    return [req for req in reqs if not req.startswith('importlib')]


def setup(**kwargs):
    """
    Call the regular `setuptools.setup` function with data read from
    our setup.cfg file.

    Parameters
    ----------
    kwargs : arguments dictionary
        Override any of the default `setuptools.setup` keyword arguments.

    """
    # Setup all our packaging config
    config.setup_org_config(kwargs.get('org_config'))

    set_working_dir()
    # Base set of defaults
    call_args = dict(
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
        zip_safe=False,
        namespace_packages=[],
        cmdclass={
          'develop': develop.develop,
          'egg_info': egg_info.egg_info,
          'jenkins': jenkins.jenkins,
          'update': update.update,
          'depgraph': depgraph.depgraph,
          'pyinstall': pyinstall.pyinstall,
          'build_sphinx': build_sphinx.build_sphinx,
          'build_ext': build_ext.build_ext,
          'build_ext_static_interpreter':
                build_ext_static_interpreter.build_ext_static_interpreter,
          'ext_gcov_test': ext_gcov_test.ext_gcov_test,
          'test_egg': test_egg.test_egg,
          'upload': upload.upload,
          'register': register.register,
          'upload_docs': upload_docs.upload_docs,
          'deploy': deploy.deploy,
          'cleanup': cleanup.cleanup,
          'tidy': tidy.tidy,
          'config': config_cmd.config,
          'release_externals': release_externals.release_externals,
          # Uninstall synonyms
          'uninstall': pyuninstall.pyuninstall,
          'remove': pyuninstall.pyuninstall,
          # Test synonyms
          'test': test.test,
          'nosetests': test.test,
          'pytest': test.test,
    })

    # Get the package metadata from the setup.cfg file
    metadata = config.parse_pkg_metadata(config.get_pkg_cfg_parser())

    # Determine namespace packages based off of the name
    call_args['namespace_packages'] = get_namespace_packages(metadata['name'])

    # Update the long description based off of README,CHANGES etc.
    metadata['long_description'] = get_pkg_description(metadata)

    # Overrides from setup.cfg file.
    # Console_scripts is a bit special in this regards as it lives under
    # entry_points
    call_args.update(metadata)
    if 'console_scripts' in call_args:
        call_args['entry_points']['console_scripts'] = \
            call_args['console_scripts']
        del(call_args['console_scripts'])

    # Overrides/Updates from call arguments.
    # Override for scalar, update for dict.
    for k, v in kwargs.items():
        if type(v) is dict and k in call_args:
            call_args[k].update(v)
        else:
            call_args[k] = v

    if 'install_requires' in call_args:
        call_args['install_requires'] = \
            clean_requires(call_args['install_requires'])

    # Call base setup method, retrieve distribution
    dist = _setup(**call_args)

    # Check if we've set a failed flag this may be due to a failed upload.
    if hasattr(dist, '_failed') and dist._failed:
        raise SystemExit(1)
