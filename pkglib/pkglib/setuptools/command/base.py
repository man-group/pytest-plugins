import sys
import os.path
import string
from distutils.fancy_getopt import longopt_xlate
from distutils import log

from setuptools.command.easy_install import easy_install

from pkglib.setuptools.patches import patch_httplib
from pkglib import manage, cmdline, CONFIG


def _banner(msg):
    from termcolor import colored
    w = (120 - len(msg) - 6)
    log.info('')
    log.info(colored("#-- %s %s#" % (msg, w * '-'), 'red', attrs=['bold']))
    log.info('')


class CommandMixin(object):
    """ Common command methods """
    def banner(self, msg):
        """ Prints a banner text to the terminal.
        """
        _banner(msg)

    # TODO: self.distribution will fail when this class is instantiated on its own.
    #       maybe base this from Command as well

    def _run(self, command_object, command_name):
        with patch_httplib() as status_codes:
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

    def get_easy_install_cmd(self, build_only=False, **kwargs):
        """ Returns a correctly setup easy_install cmd class for passing
            into `pkglib.setuptools.buildout.install`.
            Lifted from `setuptools.dist`

            Parameters
            ----------
            build_only : `bool`
                Configured for build and testing packages - these will be
                installed into the directory returned from
                `pkglib.manage.get_build_egg_dir`

            kwargs:
                Other kwargs to pass to easy_install constructor

            Returns
            -------
            cmd : `setuptools.Command`
                Configured command-class
        """
        dist = self.distribution.__class__({'script_args': ['easy_install']})
        dist.parse_config_files()

        if build_only:
            cmd = easy_install(
                dist, args=["x"], install_dir=manage.get_build_egg_dir(),
                exclude_scripts=True, always_copy=False, build_directory=None,
                editable=False, upgrade=False, multi_version=True,
                no_report=True, **kwargs)
        else:
            cmd = easy_install(dist, args=['x'], **kwargs)

        cmd.ensure_finalized()
        return cmd

    def fetch_build_eggs(self, reqs, prefer_final=True, use_existing=False):
        """ Uses the buildout installer for fetching setup requirements.
            Mostly lifted from setuptools.dist

            Parameters
            ----------
            reqs : `list`
                List if package requirements
            prefer_final : `bool`
                Prefer non-dev versions of package dependencies
            use_existing : `bool`
                Will use eggs found in working set, and not try and update
                them if it can
        """
        # Lazy import for bootstrapping
        from pkglib.setuptools.buildout import install
        # Run the installer, set the option to add to global working_set
        # so other commands in this run can use the packages.

        # Setting build_only to false here now, as we don't
        # really need to have the feature whereby test and build eggs are
        # installed in the cwd(), it just makes a mess of people's home
        # directories.
        if hasattr(self, 'index_url'):
            url = self.maybe_add_simple_index(self.index_url)
        else:
            url = self.maybe_add_simple_index(CONFIG.pypi_url)
        cmd = self.get_easy_install_cmd(build_only=False, index_url=url)
        return install(cmd, reqs, add_to_global=True, prefer_final=prefer_final,
                       use_existing=use_existing)

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
                url += '/root/pypi/+simple/' 
        return url

    def get_site_packages(self):
        """ Returns the site-packages dir for this virtualenv
        """
        return manage.get_site_packages()
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
        cmd = ("lsof 2>/dev/null | grep {} |"
               "awk '{{ print $2 \" \" $9 }}'").format(self.site_packages)
        return [i.split() for i in
                cmdline.run(cmd, capture_stdout=True, check_rc=False,
                            shell=True).split('\n') if i]

    def create_relative_link(self, src, dest):
        """ Create relative symlink from src -> dest
        """
        with manage.chdir(os.path.dirname(src)):
            os.symlink(dest, os.path.basename(src))

    def parse_multiline(self, val):
        """ Turn multiline .ini entries into a list
        """
        if not val:
            return []
        return [i.strip() for i in val.split('\n') if i.strip()]
