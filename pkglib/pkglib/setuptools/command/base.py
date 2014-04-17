import sys
import os.path
import string
import itertools
from distutils.fancy_getopt import longopt_xlate
from distutils import log

from pkg_resources import resource_filename
from setuptools.dist import Distribution

from pkglib.setuptools.patches.http import patch_http
from pkglib_util import cmdline
from pkglib import CONFIG, util
from pkglib.config import parse


def get_resource_file(name, path=None):
    """ Returns the path to a resource file by name.
        Default path for the files is the 'resources' directory
    """
    if path is None:
        pkg = __name__
        name = os.path.join('resources', name)
    else:
        pkg = path
    return resource_filename(pkg, name)


def merge_options(*opts):
    final_opts = []
    for opt in (o for opt_list in opts for o in opt_list):
        existing = [o for o in final_opts if o[0] == opt[0]]
        if existing:
            final_opts.remove(existing[0])
        final_opts.append(opt)

    return final_opts


def write_text(f, text):
    with open(f, "wt") as f:
        f.write(text)


def _banner(msg):
    """ Writes a banner to the distutils log
    """
    from termcolor import colored
    w = (120 - len(msg) - 6)
    log.info('')
    log.info(colored("#-- %s %s#" % (msg, w * '-'), 'red', attrs=['bold']))
    log.info('')


def get_easy_install_cmd(distribution, build_only=False, **kwargs):
    """ Returns a correctly setup easy_install cmd class for passing
        into `pkglib.setuptools.buildout.install`.
        Lifted from `setuptools.dist`

        Parameters
        ----------
        distribution : `distutils.Distribution`
            the main distribution
        build_only : `bool`
            Configured for build and testing packages - these will be installed
            into the directory returned from:

            `pkglib.util.get_build_egg_dir`

        kwargs:
            Other kwargs to pass to easy_install constructor

        Returns
        -------
        cmd : `setuptools.Command`
            Configured command-class
    """
    # late import to resolve circularity
    from pkglib.setuptools.command.easy_install import easy_install

    dist = distribution.__class__({'script_args': ['easy_install']})
    dist.parse_config_files()
    dist.verbose = getattr(distribution, 'verbose', 1)
    dist.dry_run = getattr(distribution, 'dry_run', 0)

    if build_only:
        cmd = easy_install(
            dist, args=["x"], install_dir=util.get_build_egg_dir(),
            exclude_scripts=True, always_copy=False, build_directory=None,
            editable=False, upgrade=False, multi_version=True, no_report=True,
            **kwargs)
    else:
        cmd = easy_install(dist, args=['x'], **kwargs)

    cmd.ensure_finalized()
    return cmd


def fetch_build_eggs(reqs, dist=None, prefer_final=True, use_existing=False,
                     add_to_env=False):
    """ Uses the buildout installer for fetching setup requirements.
        Mostly lifted from setuptools.dist

        Parameters
        ----------
        reqs : `list`
            List if package requirements
        dist : `distutils.dist.Distribution`
            the main distribution
        prefer_final : `bool`
            Prefer non-dev versions of package dependencies
        use_existing : `bool`
            Will use eggs found in working set, and not try and update them if
            it can
        add_to_env : `bool`
            whether distributions should be added to the virtual environment
    """
    # Lazy imports here to allow pkglib to bootstrap itself.
    from pkglib.setuptools.buildout import install

    # Run the installer and set the option to add to the global working_set
    # so that other commands in this run can use the packages straight away.

    # Setting build_only to false here now, as we don't want build eggs
    # installed in the cwd(), it just makes a mess of people's home directories.

    # Also setting pth_file to None in order to disable polluting virtual
    # environment with distributions required only during setup

    if not dist:
        dist = Distribution(attrs=dict(name="pkglib.fetcher", version="1.0.0"))
    cmd = get_easy_install_cmd(dist, exclude_scripts=not add_to_env)

    if not add_to_env:
        cmd.pth_file = None

    return install(cmd, reqs, add_to_global=True, prefer_final=prefer_final,
                   use_existing=use_existing)


class CommandMixin(object):
    """ Common command methods """

    def banner(self, msg):
        """ Prints a banner text to the terminal.
        """
        _banner(msg)

    # TODO: self.distribution will fail when this class is instantiated on its own.
    #       maybe base this from Command as well

    def _run(self, command_object, command_name):
        with patch_http() as status_codes:
            command_object.run(self)
        if not status_codes:
            log.error("Couldn't determine success or failure of %s" % command_name)
            self.distribution._failed = True
        else:
            #   Only check against the last received code in case of redirects, retries etc.
            final_status_code = status_codes[-1]
            if final_status_code not in self._ok_status_codes:
                log.error("Final status code for upload was unexpected: %r! "
                    "all status codes: %r" % (final_status_code, status_codes))
                self.distribution._failed = True

    def get_requirements(self, extras=False, test=False):
        """ Get a set of all our requirements

        Parameters
        ----------
        extras : `bool`
            Include extras_require
        test : `bool`
            Include tests_require

        """
        install_reqs = self.distribution.install_requires
        install_reqs = install_reqs[:] if install_reqs else []

        if test:
            install_reqs += self.distribution.tests_require or []

        if extras:
            extras_reqs = self.distribution.extras_require
            if extras_reqs:
                install_reqs += list(itertools.chain(*extras_reqs.values()))

        return set(install_reqs)

    def maybe_add_simple_index(self, url):
        """Checks if the server URL should have a /simple on the end of it.
           This is to get around the brain-dead difference between
           upload/register and easy_install URLs.
        """
        # Lazy import as they might be a child class of this one
        import pyinstall
        import develop
        import test
        if url and (isinstance(self, pyinstall.pyinstall) or
                    isinstance(self, develop.develop) or
                    isinstance(self, test.test)):
            # Vanilla PyPI
            if CONFIG.pypi_variant is None and not url.endswith('/simple')  \
                                           and not url.endswith('/simple/'):
                url += '/simple'

            # DevPI. TODO: use pip.conf / pydistutils.cfg for all of this
            elif CONFIG.pypi_variant == 'devpi':
                url += '/+simple/'
        return url

    def get_site_packages(self):
        """ Returns the site-packages dir for this virtualenv
        """
        from pkglib import pyenv
        return pyenv.get_site_packages()
    site_packages = property(get_site_packages)

    def run_cleanup_in_subprocess(self):
        """ Runs the cleanup job in a subprocess. Necessary as setup.py is
            often changing the state of the virtualenv as it goes, and
            working_set in memory might not reflect the real state of the world
        """
        # Using the entry point here instead of the module. This is because the
        # module may have been moved by the time we go to run it, eg if we just
        # updated pkglib itself.
        cmd = [sys.executable,
               os.path.join(sys.exec_prefix, 'bin', 'pycleanup')]
        for arg in ['-v', '-n', '--verbose', '--dry-run']:
            if arg in sys.argv:
                cmd.append(arg)
        cmdline.run(cmd, capture_stdout=False)

    def get_option_list(self):
        """ Returns a list of configured options for this command.
        """
        res = []
        for (option, _, _) in self.user_options:
            option = string.translate(option, longopt_xlate)
            if option[-1] == "=":
                option = option[:-1]
            value = getattr(self, option)
            res.append((option, value))
        return res

    def get_open_files(self):
        """ Returns open files under our site-packages
        """
        # It's far cheaper to run lsof for all files and search later than
        # running it with the +D option to only return results under a certain
        # directory
        # TODO: this might not be on the path, and be hidden by the >/dev/null
        cmd = ("lsof 2>/dev/null | grep {0} |"
               "awk '{{ print $2 " " $9 }}'").format(self.site_packages)
        return [i.split() for i in
                cmdline.run(cmd, capture_stdout=True, check_rc=False,
                            shell=True).split('\n') if i]

    def create_relative_link(self, src, dest):
        """ Create relative symlink from src -> dest
        """
        with cmdline.chdir(os.path.dirname(src)):
            os.symlink(dest, os.path.basename(src))

    def parse_multiline(self, val):
        """ Turn multiline .ini entries into a list
        """
        if not val:
            return []
        return parse.parse_multi_line_value(val)
