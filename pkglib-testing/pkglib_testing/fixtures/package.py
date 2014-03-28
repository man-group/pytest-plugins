""" Python package fixtures
"""
import os

from pkglib_util.six.moves import configparser

from .venv import TmpVirtualEnv


def pytest_funcarg__pkg_template(request):
    """ Create a new package from the core template in a temporary workspace.
        Cleans up on exit.
    """
    return request.cached_setup(
        setup=PkgTemplate,
        teardown=lambda p: p.teardown(),
        scope='function',
    )

class PkgTemplate(TmpVirtualEnv):
    """
    Creates a new package from the package templates in a temporary workspace.
    Cleans up on exit.

    Attributes
    ----------
    vcs_uri : `str`
        path to a local repository for this package
    trunk_dir : `path.path`
        path to the trunk package directory
    """

    def __init__(self, name='acme.foo-1.0.dev1', **kwargs):
        """
        Parameters
        ----------
        name : `str`
            package name

        kwargs: any other config options to set
        """
        TmpVirtualEnv.__init__(self)
        self.name = name

        # Install pkglib
        self.install_package('pkglib', installer='easy_install', build_egg=True)

        self.vcs_uri, self.trunk_dir = create_package_from_template(self, name, **kwargs)

def create_package_from_template(venv, name, template="pkglib_project", paster_args="", metadata=None,
                                 repo_base="http://test_repo_base", dev=True, install_requires=None, **kwargs):
    metadata = {} if metadata is None else dict(metadata)
    if '-' in name:
        pkg_name, _, version = name.rpartition('-')
        pkg_name = metadata.setdefault('name', pkg_name)
        version = metadata.setdefault('version', version)
        dev = (version.rpartition('.')[2] == 'dev1')
        if dev:
            metadata['version'] = version = version.rpartition('.')[0]
    else:
        pkg_name = metadata.setdefault('name', name)
        version = metadata.setdefault('version', '1.0.0.dev1' if dev else '1.0.0')
    if install_requires is not None:
        if not isinstance(install_requires, str):
            install_requires = '\n'.join(install_requires)
        metadata['install_requires'] = install_requires

    venv.run('{python} {virtualenv}/bin/pymkproject -t {template_type} {name} '
             '--no-interactive {paster_args}'.format(python=venv.python,
                                                     virtualenv=venv.virtualenv,
                                                     name=pkg_name,
                                                     template_type=template,
                                                     paster_args=paster_args), capture=True)
    if name != pkg_name:
        os.rename(venv.workspace / pkg_name, venv.workspace / name)
    vcs_uri = '%s/%s' % (repo_base, pkg_name)
    trunk_dir = venv.workspace / name / 'trunk'
    update_setup_cfg(trunk_dir / 'setup.cfg', vcs_uri=vcs_uri, metadata=metadata, dev=dev, **kwargs)
    return vcs_uri, trunk_dir


def update_setup_cfg(cfg, vcs_uri, metadata={}, dev=True, **kwargs):
    # Update setup.cfg
    c = configparser.ConfigParser()
    c.read(cfg)
    _metadata = dict(
        url=vcs_uri,
        author='test',
        author_email='test@test.example',
    )
    _metadata.update(metadata)
    for k, v in _metadata.items():
        c.set('metadata', k, v)

    if not dev:
        c.remove_option('egg_info', 'tag_build')
        c.remove_option('egg_info', 'tag_svn_revision')

    for section, vals in kwargs.items():
        if not c.has_section(section):
            c.add_section(section)
        for k, v in vals.items():
            c.set(section, k, v)

    with open(cfg, 'w') as cfg_file:
        c.write(cfg_file)
