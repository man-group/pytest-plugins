import io
import imp
import os
import shutil
import sys
import tempfile

try:  # Python 2
    str_type = basestring
    unicode_type = unicode
    _open_func_path = '__builtin__.open'
except NameError:  # Python 3
    str_type = str
    unicode_type = str
    _open_func_path = 'builtins.open'
    from functools import reduce

from collections import defaultdict
from contextlib import contextmanager
from itertools import chain

import pkg_resources

from mock import Mock, patch, ANY, call
from pkg_resources import (Distribution, NullProvider, Requirement, WorkingSet,
                           Environment, DistributionNotFound, normalize_path)
from setuptools import Command

import pkglib  # @UnusedImport  sets up patches

try:
    # Python 3
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

from pkglib.scripts import run_setup_command
from pkglib.setuptools.buildout import Installer
from pkglib.setuptools.command import base

from pkglib.setuptools.command.easy_install import easy_install
from setuptools.command.easy_install import PthDistributions

_original_installer_init = Installer.__init__
_original_is_dir = os.path.isdir

_root_dir_prefix = os.path.splitdrive(sys.executable)[0] or os.path.sep

_easy_install_cmd = "pkglib.setuptools.command.easy_install.easy_install"
_easy_install_chmod = "setuptools.command.easy_install.chmod"
_easy_install_get_site_dirs = "setuptools.command.easy_install.get_site_dirs"
_ei_find_distributions = "setuptools.command.easy_install.find_distributions"
_easy_install_mocks = "____ei_mocks"
_pkgr_default_ws = "pkg_resources.working_set"
_pkgr_ws = "pkg_resources.WorkingSet"

_proc_dist_spy = "proc_dist"
_chmod_spy = "chmod"
_written_scripts = "written_scripts"
_written_pth_files = "written_pth"
_update_pth_spy = "updated_pth"

TEST_SITE_DIR = "/<test_site_dir>"


# TODO: majority of supporting infrastructure defined here needs to be moved
# to pkglib_testing

class SavedBytesIO(io.BytesIO):

    def close(self):
        self.value = self.getvalue()
        self.string_value = self.value.decode('utf-8')

    def write(self, b):
        if isinstance(b, str_type):
            b = b.encode('utf-8')
        io.BytesIO.write(self, b)


class ETextIOWrapper(io.TextIOWrapper):

    def write(self, s):
        io.TextIOWrapper.write(self, s if isinstance(s, unicode_type)
                               else unicode_type(s, ('utf-8')))


class Req(object):
    def __init__(self, project_name, specs):
        self.project_name = project_name
        self.specs = specs


class Pkg(object):
    def __init__(self, name, requires, src=False, location=None,
                 version='1.0.0'):
        self.project_name = name
        self._requires = requires
        self.version = version
        if location is None:
            if src:
                self.location = "/path/to/somewhere"
            else:
                self.location = "/path/to/an.egg"
        else:
            self.location = location

    def __repr__(self):
        return "<%s>" % self.project_name

    def requires(self):
        return self._requires


class TestCmd(Command, base.CommandMixin):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass


class DummyCmd(TestCmd):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        pass


class EggInfo(DummyCmd):
    broken_egg_info = False
    egg_base = "."
    egg_name = "dummy.egg"
    egg_info = "foo"


class SandboxedEasyInstall(object):

    def __init__(self, base_type, mocks, virtualenv_dists, available_dists,
                 attrs={}):
        self.base_type = base_type
        self.virtualenv_dists = virtualenv_dists
        self.available_dists = available_dists
        self.attrs = attrs
        self.mocks = mocks

        if _easy_install_mocks in mocks:
            self._eim = mocks[_easy_install_mocks]
        else:
            self._eim = {}
            self._eim[_proc_dist_spy] = Mock()
            self._eim[_chmod_spy] = Mock()
            self._eim[_written_scripts] = defaultdict(SavedBytesIO)
            self._eim[_written_pth_files] = defaultdict(SavedBytesIO)
            self._eim[_update_pth_spy] = Mock()

            mocks[_easy_install_mocks] = self._eim

    def finalize_options(self):
        with patch("pkg_resources.Environment.scan",
                   new=_get_patched_scan_method(self.virtualenv_dists)):
            self.base_type.finalize_options(self)

        for d in self.virtualenv_dists:
            self.local_index.add(d)

        _sandbox_package_index(self.package_index, self.available_dists)
        self.sitepy_installed = True  # do not fiddle with file system
        for k, v in self.attrs.items():
            setattr(self, k, v)

    def write_script(self, *args, **kwargs):
        with ExitStack() as stack:
            ec = stack.enter_context
            ec(_patch_open(self._eim[_written_scripts]))
            ec(_patch_is_dir(exists=self.script_dir))
            ec(patch(_easy_install_chmod, new=self._eim[_chmod_spy]))

            self.base_type.write_script(self, *args, **kwargs)

    def process_distribution(self, requirement, dist, deps=True, *info):
        self._eim[_proc_dist_spy](requirement, dist, deps=deps, *info)
        self.base_type.process_distribution(self, requirement, dist,
                                            deps=deps, *info)

    def install_eggs(self, spec, download, tmpdir):
        match = [d for d in self.available_dists if d in spec]
        return match if match else self.base_type.install_eggs(self, spec,
                                                               download, tmpdir)

    def check_site_dir(self):
        self.install_dir = TEST_SITE_DIR

        # In order for ".pth" write test to succeed
        with ExitStack() as stack:
            stack.enter_context(_patch_open())
            stack.enter_context(patch("os.unlink", new=lambda _f: None))

            self.base_type.check_site_dir(self)

    def check_pth_processing(self):
        return True

    def update_pth(self, dist):
        self._eim[_update_pth_spy](dist)
        with ExitStack() as stack:
            stack.enter_context(_patch_open(self._eim[_written_pth_files]))
            stack.enter_context(patch("os.unlink", new=lambda _f: None))

            self.base_type.update_pth(self, dist)


class ImportMocker(object):

    def __init__(self, modules={}):
        self.__modules = dict()
        for m, i in modules.items():
            self.add_module(m, i)

    def add_module(self, fullname, attrs):
        module_path = fullname.split(".")

        m = ""

        for n in module_path:
            p = ((m + ".") if m else "") + n

            if p not in self.__modules:
                new_module = imp.new_module(p)
                new_module.__loader__ = self
                new_module.__file__ = ["fake module [%s]" % p]
                new_module.__path__ = []
                new_module.__package__ = p

            if m in sys.modules:
                setattr(sys.modules[m], n, new_module)

            m = p

        def create_module_func(acc, val):
            p = (acc + "." + val) if acc else val
            if p not in self.__modules:
                new_module = imp.new_module(p)
                new_module.__loader__ = self
                new_module.__file__ = ["fake module [%s]" % p]
                new_module.__path__ = []
                new_module.__package__ = p
                self.__modules[p] = new_module
            return p

        m = reduce(create_module_func, module_path, "")

        if m in sys.modules:
            sys.modules[fullname] = self.__modules[m]

        for k, v in attrs.items():
            setattr(self.__modules[m], k, v)

    def find_module(self, fullname, path=None):  # @UnusedVariable
        if fullname in self.__modules:
            return self
        return None

    def load_module(self, name):
        sys.modules[name] = self.__modules[name]
        return self.__modules[name]


class _DictMetaProvider(NullProvider):

    def __init__(self, metadata, **kwargs):
        self.egg_info = "_"

        self.files = dict((self.egg_info + os.path.sep + k, v)
                          for k, v in metadata.items())
        self.dirs = set(list(chain(*[reduce(lambda acc, val: acc
                                            + [os.path.join(acc[-1], val)],
                                            [os.path.split(f)[0]], [""])
                                     for f in self.files])))
        self.metadata = self
        self.__dict__.update(kwargs)

    def _has(self, path):
        return path in self.files

    def _get(self, path):
        return self.files.get(path)

    def _isdir(self, path):
        return path in self.dirs

    def _listdir(self, path):
        return [sf[1] for sf in (os.path.split(f) for f in self.files)
                if sf[0] == path]

    def __getattr__(self, attr):
        if attr in self.files:
            return self.files[attr]

        fn_attr = self._fn(self.egg_info, attr)
        if fn_attr in self.files:
            return self.files[fn_attr]

        return object.__getattr__(self, attr)


def _make_root_dir_from(dirname):
    return (dirname if dirname.startswith(_root_dir_prefix)
            else _root_dir_prefix + dirname)


def _find_distributions(*dists):
    return [pkg_resources.working_set.find(Requirement.parse(pkg_name))
            for pkg_name in dists]


def _create_easy_install_mock(dist, available_dists=[]):
    easy_install_mock = Mock(install_dir="foo", index_url="",
                             distribution=dist)
    easy_install_mock.return_value = easy_install_mock
    easy_install_mock.local_index = Environment()
    for dist in available_dists:
        easy_install_mock.local_index.add(dist)
    return easy_install_mock


def _req_lines_from_dict(pkg_dict):
    return "\n".join("%s%s" % (k, ("" if v is None else
                                   v if v[0] in '<=>:' else
                                   "==%s" % v))
                     for k, v in pkg_dict.items())


def _create_requires_list(req_dict):
    return "" if not req_dict else _req_lines_from_dict(req_dict)


def create_dist(name, version, requires={}, setup_requires={},
                extras_require={}, tests_require=[], extra_egg_info=None,
                location=None):

    if location is None:
        location = name

    if extra_egg_info is None:
        extra_egg_info = {}

    metadata = {}
    metadata.update(extra_egg_info)
    requires = _req_lines_from_dict(requires)
    metadata["install_requires"] = requires

    if extras_require:
        extras_list = "\n".join("[%s]\n%s\n" % (n, "\n".join(extras))
                                for n, extras in
                                ((k, [v] if isinstance(v, str_type) else v)
                                 for k, v in extras_require.items()))
        requires = requires + "\n" + extras_list

    metadata['requires.txt'] = requires.encode('utf-8')

    metadata["setup_requires"] = _create_requires_list(setup_requires)
    metadata["setup_requires"] = metadata["setup_requires"].splitlines()

    metadata = _DictMetaProvider(metadata, name=name)
    d = Distribution(project_name=name, version=version, metadata=metadata,
                     location=location)
    d.tests_require = tests_require
    return d


def _add_mock(mocks, mock_id, setup_func=lambda: Mock(), replace=False):
    if mock_id in mocks and not replace:
        return

    mocks[mock_id] = setup_func()


def _get_mock(mocks, mock_id, setup_func=lambda: Mock()):
    if mock_id not in mocks:
        mocks[mock_id] = setup_func()

    return mocks[mock_id]


def _get_mock_dict(mocks, mock_id, original_dict=None):
    if mock_id in mocks:
        return mocks[mock_id]

    if original_dict is None:
        mock_id_split = mock_id.split('.')
        m = __import__(".".join(mock_id_split[:-1]))
        val = getattr(m, mock_id_split[-1])
    else:
        val = original_dict

    mocks[mock_id] = val = dict(val)
    return val


def _add_mock_dict(mocks, mock_id, setup_func=None, original_dict=None):
    d = _get_mock_dict(mocks, mock_id, original_dict)
    return setup_func(d) if setup_func else d


def _add_module_mock(mocks, module_path, attrs={}):

    def init_import_mocker():
        return ([ImportMocker()] + list(sys.meta_path))

    importer = _get_mock(mocks, "sys.meta_path", init_import_mocker)[0]
    importer.add_module(module_path, attrs)


@contextmanager
def patch_env(env_dict):
    with patch.dict(os.environ, env_dict):
        yield


def _get_open_mock(file_dict):

    def open_func(f, mode=""):
        file_io = file_dict[f]
        file_io.seek(0)
        if 't' in mode:
            file_io = ETextIOWrapper(file_io, 'utf-8')
        return file_io

    mock_open = Mock()
    mock_open.side_effect = open_func
    return mock_open


@contextmanager
def _patch_open(file_dict=None):
    if file_dict is None:
        file_dict = defaultdict(SavedBytesIO)

    with patch(_open_func_path, new=_get_open_mock(file_dict)):
        yield file_dict


@contextmanager
def _patch_is_dir(exists=[], not_exists=[]):

    def patched_is_dir(dirname):

        if dirname in exists:
            return True

        if dirname in not_exists:
            return False

        return _original_is_dir(dirname)

    with patch("os.path.isdir", side_effect=patched_is_dir):
        yield


@contextmanager
def _mock_modules(modules):
    importer = ImportMocker(modules=modules)
    with patch("sys.meta_path", new=sys.meta_path + [importer]):
        yield


def _get_patched_find_packages(available_dists):

    def find_packages(requirement):
        return max(d for d in available_dists if d in requirement)

    return find_packages


def _get_patched_fetch_distribution(available_dists):

    def fetch_distribution(spec, *ars, **kwargs):  # @UnusedVariable
        match = [d for d in available_dists if d in spec]
        return match[0] if match else None

    return fetch_distribution


def _get_patched_scan_method(virtualenv_dists):

    def scan(self, *args, **kwargs):  # @UnusedVariable # NOQA
        for d in virtualenv_dists:
            self.add(d)

    return scan


def _add_working_set_mocks(mocks, virtualenv_dists):
    ws = WorkingSet(entries=[])
    [ws.add(d) for d in _find_distributions('setuptools', 'zc.buildout')]
    [ws.add(d) for d in virtualenv_dists]

    default_ws = WorkingSet(entries=ws.entries)
    [default_ws.add(d) for d in virtualenv_dists]

    _add_mock(mocks, _pkgr_ws,
              lambda: Mock(side_effect=lambda entries: ws if entries
                           else WorkingSet([])))
    _add_mock(mocks, _pkgr_default_ws, lambda: default_ws)


def _add_get_dist_mock(mocks, dists):

    def _get_dist(req, ws, always_unzip):  # @UnusedVariable
        match = [d for d in dists if d in req]
        if match:
            return match
        raise DistributionNotFound(req)

    _add_mock(mocks, "pkglib.setuptools.buildout.Installer._get_dist",
              lambda: Mock(side_effect=_get_dist))


def _add_buildout_installer_init_mock(mocks, virtualenv_dists, available_dists):

    def __init__(self, *args, **kwargs):

        def scan(self, *args, **kwargs):  # @UnusedVariable # NOQA
            for d in virtualenv_dists + available_dists:
                self.add(d)

        with patch("pkg_resources.Environment.scan", new=scan):
            _original_installer_init(self, *args, **kwargs)
            self._index.find_packages = (_get_patched_find_packages
                                         (available_dists))

    _add_mock(mocks, "pkglib.setuptools.buildout.Installer.__init__",
              lambda: __init__)


def _prepare_cmd(cmd, dist, tmpdir):

    class patched_cmd(cmd):

        def finalize_options(self):
            cmd.finalize_options(self)
            self.dist = dist
            self.egg_path = tmpdir
            self.egg_link = tempfile.mkstemp(dir=tmpdir)[1]

    patched_cmd.__name__ = cmd.__name__
    return patched_cmd


def _sandbox_package_index(index, dists):
    index.fetch_distribution = _get_patched_fetch_distribution(dists)


def _sandbox_easy_install(mocks, cmd, virtualenv_dists, available_dists,
                          attrs={}):
    class patched_easy_install(SandboxedEasyInstall, cmd):
        def __init__(self, *args, **kwargs):
            SandboxedEasyInstall.__init__(self, cmd, mocks,
                                          virtualenv_dists, available_dists,
                                          attrs)
            cmd.__init__(self, *args, **kwargs)
    patched_easy_install.__name__ = cmd.__name__
    return patched_easy_install


def _prepare_easy_install_cmd(mocks, cmd, virtualenv_dists, available_dists,
                              attrs={}):
    """Creates a sand-boxed version of an easy_install command.
    The patched command operates in a sand-box virtual environment
    containing only specified distributions. Remote package resolution is
    also limited to provided set of 'available' distributions.

    Parameters
    ----------
    cmd : `distutils.Command`
        original distutils/setuptools command. If it is an instance
        of `easy_install` it will be used a base, otherwise a
        vanilla `easy_install` is used as a base
    virtualenv_dists : `list<pkg_resources.Distribution>`
        distributions installed in the environment
    available_dists : `list<pkg_resources.Distribution>`
        distributions available for fetching
    """

    easy_install_cmd = _sandbox_easy_install(mocks, easy_install,
                                             virtualenv_dists,
                                             available_dists, attrs)
    if cmd is easy_install:
        cmd = easy_install_cmd
    elif issubclass(cmd, easy_install):
        cmd = _sandbox_easy_install(mocks, cmd, virtualenv_dists,
                                    available_dists, attrs)
    _add_mock(mocks, _easy_install_cmd, lambda: easy_install_cmd)

    _add_mock(mocks, _easy_install_get_site_dirs,
              lambda: Mock(return_value=[TEST_SITE_DIR]))

    return cmd


def _cleanup_mock(self):
    print("Clean-up is skipped (mocked)")


def _prepare_distribution_metadata(cmd, dist):
    attrs = {}
    attrs['setup_requires'] = getattr(dist, 'setup_requires', [])
    attrs['install_requires'] = [str(req) for req in
                                 (dist.requires() if dist else [])]
    attrs['tests_require'] = getattr(dist, 'tests_require', [])
    attrs['extras_require'] = (dict((extra, [str(r) for r in
                                             dist.requires([extra])])
                                    for extra in dist.extras)
                               if dist else {})
    attrs['cmdclass'] = {cmd.__name__: cmd}
    attrs['packages'] = []
    attrs['namespace_packages'] = []
    attrs['verbose'] = 2

    return attrs


def assert_dists_in_pth(mocks, *dists):

    # Check that only the required distributions were added to "*.pth" file
    pth_file = [f for n, f in
                mocks[_easy_install_mocks][_written_pth_files].items()
                if os.path.basename(n) == "easy-install.pth"]

    pth_file = pth_file[0] if pth_file else io.BytesIO()

    dists = list(dists)

    pth_filename = "/<pth_file>"
    base_d = normalize_path(os.path.dirname(pth_filename))

    def find_distributions(path_item, only=False):  # @UnusedVariable
        d = [d for d in dists
             if normalize_path(os.path.join(base_d, d.location)) == path_item]
        assert len(d) == 1, ("Distribution on path [%s] should not have "
                             "been added to '.pth' file" % str(path_item))
        dists.remove(d[0])
        return []

    pth_file_dict = {pth_filename: pth_file}
    pth_file.seek(0)

    with ExitStack() as stack:
        ec = stack.enter_context
        ec(_patch_open(pth_file_dict))
        ec(patch("os.path.exists", new=lambda _: True))
        ec(patch("os.path.isfile", new=lambda f: f == pth_filename))
        ec(patch(_ei_find_distributions, new=find_distributions))

        PthDistributions(pth_filename)

    assert not dists, ("[%d] distributions were not added to the '.pth' "
                       "file: %s" % (len(dists), str(dists)))


def assert_dists_installed(mocks, *dists):
    """Checks specified distributions were fetched/processed. This merely
    checks that a distribution was processed, which does not mean it
    actually got installed.

    To check whether distribution was added to a persistent environment, use
    `assert_dists_in_pth`.
    """

    proc_dist_mock = mocks[_easy_install_mocks][_proc_dist_spy]

    # Check distributions were processed
    calls = [call(ANY, d, deps=False) for d in dists]
    proc_dist_mock.assert_has_calls(calls, any_order=True)

    # Check that only expected distributions were processed
    assert len([c for c in proc_dist_mock.call_args_list
                if c[0][1] not in dists]) == 0


def assert_scripts_written(mocks, scripts):
    written_scripts = mocks[_easy_install_mocks][_written_scripts]
    written_scripts = dict((name, content) for name, content in
                           ((os.path.split(k)[1], v.string_value)
                            for k, v in written_scripts.items())
                           if name in scripts)

    assert written_scripts == scripts


def run_setuptools(f, cmd, dist=None, dist_attrs=None, args=None,
                   virtualenv_dists=[], available_dists=[], mocks=None):
    """Runs `setup()` of `setuptools` in a sand-boxed environment.

    Parameters
    ----------
    f : `function`
        function which runs `setup()`
    cmd : `distutils.cmd.Command`
        command to be tested
    dist : pkg_resources.Distribution`
        main distribution. Known attributes of this distribution
        (e.g. 'setup_requires') will be passed as keyword arguments
        to `f()`.
    dist_attrs : additional attributes to pass to `f()`
    virtualenv_dists : `list<pkg_resources.Distribution>`
        distributions installed in the environment
    available_dists : `list<pkg_resources.Distribution>`
        distributions available for fetching
    mocks : `dict<str, mock.Mock>`
        mocks to use
    """

    if mocks is None:
        mocks = {}

    if dist_attrs is None:
        dist_attrs = {}

    if args:
        dist_attrs['argv'] = args if args else [cmd.__name__]

    # Temporary directory to be used for all testing output if required
    tmpdir = tempfile.mkdtemp()

    # Prepare the main command
    cmd = _prepare_cmd(cmd, dist, tmpdir)
    _add_get_dist_mock(mocks, virtualenv_dists + available_dists)
    _add_buildout_installer_init_mock(mocks, virtualenv_dists, available_dists)

    # Patch `easy_install` and all related commands
    easy_install_attrs = {}
    easy_install_attrs['script_dir'] = dist_attrs.get('script_dir',
                                                      "<test_script_dir>")

    cmd = _prepare_easy_install_cmd(mocks, cmd, virtualenv_dists,
                                    available_dists, attrs=easy_install_attrs)

    # Change default working set to contain only specified distributions
    _add_working_set_mocks(mocks, virtualenv_dists)

    # Disable clean-up
    _add_mock(mocks, "pkglib.setuptools.command.base.CommandMixin."
              "run_cleanup_in_subprocess", lambda: _cleanup_mock)

    # Set command line arguments
    _add_mock(mocks, "sys.argv", lambda: sys.argv[:1])

    # Preserve system environment
    _add_mock_dict(mocks, "os.environ")

    # Clear internal index cache of `zc.buildout`
    _add_mock_dict(mocks, "zc.buildout.easy_install._indexes",
                   original_dict={})

    # Prepare distribution metadata
    attrs = _prepare_distribution_metadata(cmd, dist)
    attrs.update(dist_attrs if dist_attrs else {})
    attrs["__command"] = cmd

    # Disable `egg_info` command
    if not 'egg_info' in attrs['cmdclass']:
        attrs['cmdclass']['egg_info'] = EggInfo

    saved_set = pkg_resources.working_set
    with ExitStack() as stack:
        for n, m in mocks.items():
            if n.startswith("____"):
                continue
            should_create = getattr(m, "__create__", False)
            stack.enter_context(patch(n, create=should_create, new=m))
        try:
            f(**attrs)
        finally:
            pkg_resources.working_set = saved_set
            try:
                shutil.rmtree(tmpdir)
            except:
                pass


def run_setuptools_cmd(cmd, *args, **kwargs):

    def run_setuptools_with_patched_command(**attrs):
        patched_cmd = attrs.pop("__command")
        run_setup_command(patched_cmd, **attrs)

    run_setuptools(run_setuptools_with_patched_command, cmd, *args, **kwargs)
