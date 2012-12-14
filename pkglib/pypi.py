"""  PyPi accessor module
"""
import os
import re
import logging
import urllib2
import exceptions
import ConfigParser
import xmlrpclib
import urlparse

from xml.etree.cElementTree import ElementTree
from multiprocessing import Pool

from pkglib import CONFIG
from pkglib.errors import UserError
from pkglib.cmdline import run
from pkglib.manage import PackageVersion, is_dev_version, is_strict_dev_version


def get_log():
    return logging.getLogger('pkglib.pypi')

RE_NAMESPACE = re.compile('^{([^}]+)}.*$')


def _get_namespace(tree):
    ns = RE_NAMESPACE.match(tree.getroot().tag)
    if ns:
        return "{%s}" % ns.group(1)
    else:
        return ''


def has_pypi_xmlrpc_interface(uri):
    """
    Detect whether or not the specified server provides the PyPI XML-RPC
    interface.
    """
    url = urlparse.urljoin(uri, '/')
    client = xmlrpclib.ServerProxy(url)
    try:
        client.list_packages()
    except Exception:
        return False
    return True


class PyPiAPI(object):
    """ PyPI API object.
        Caching lookup of packages by name for their VCS uris, with
        other methods for managing PyPI Servers.
    """
    def __init__(self, uri=None, username=None, password=None):
        self._cache = {}
        if not uri:
            uri = CONFIG.pypi_url
        self.uri = uri
        if username:
            # XXX I don't think this actually works, had to turn on
            # anonymous access to get the tests passing. urllib2 really
            # does suck a bit.
            password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_manager.add_password(None, uri, username, password)
            urllib2.install_opener(urllib2.build_opener(
                urllib2.HTTPBasicAuthHandler(password_manager)))

        self.log = logging.getLogger('pkglib.pypi')
        self.log.debug('Using PyPI: %s' % self.uri)

    def resolve_dashed_name(self, pkg):
        """
        This gets around the stupid bloody problem with distutils converting all underscores
        to dashes in package names, and some third party packages being uploaded to PyPi
        with underscores regardless - most notably cx_Oracle.

        Eg::

            $ easy_install cx_Oracle
            $ pip freeze
            > cx-Oracle==5.0.3
            $ easy_install cx-Oracle
            > Requirement already satisfied: cx-Oracle==5.0.3
            $ pip uninstall cx-Oracle
            $ easy_install cx-Oracle
            > Can't satisfy requirement: cx-Oracle
            $ eat flaming death
        """
        if not '-' in pkg:
            return pkg

        if self.get_links(pkg):
            get_log().debug("Found pypi links for package %s" % pkg)
            return pkg

        underscores = pkg.replace('-', '_')
        if self.get_links(underscores):
            get_log().debug("Found pypi links for package %s" % underscores)
            return underscores

        get_log().warn("Can't find any repository links for package %s." % pkg)
        return pkg

    def get_mirror_config(self, filename="pypi_mirror.cfg"):
        """ Loads the config for mirroring eggs.
            Config format::

                [mirrors]
                keys = <mirror_name>[, <mirror_name> ]

                [<mirror_name>]
                hostname = <hostname>
                target_dir = <target file root>

            Eg::

                [mirrors]
                keys = reggie

                [reggie]
                hostname = reggie-data
                target_dir = /apps/research/python/egg_cache


            Returns
            -------
            mirrors : `list`
                List of ``{'target_host': hostname, 'target_dir', target file root}``

        """
        if not os.path.isfile(filename):
            return []
        p = ConfigParser.ConfigParser()
        p.read(filename)
        res = []
        for mirror in p.get('mirrors', 'keys').split(','):
            mirror = mirror.strip()
            res.append(dict(target_host=p.get(mirror, 'hostname'),
                            target_dir=p.get(mirror, 'target_dir')))
        return res

    def get_mirror_dirname(self, pkg_name):
        """ Returns the directory name a package will be mirrored to.
            This is a join of the first character of each namespace.
            component, capped at 2 characters.

            Parameters
            ----------
            pkg_name :
                package name

            Examples
            --------
            >>> from pkglib.pypi import PyPiAPI
            >>> PyPiAPI().get_mirror_dirname('foo')
            'f'
            >>> PyPiAPI().get_mirror_dirname('acme.foo')
            'af'
            >>> PyPiAPI().get_mirror_dirname('acme.foo.bar')
            'af'
        """
        return ''.join([i[0] for i in pkg_name.split('.', 1)])

    def get_mirror_targets(self, file_root, target_root, target_packages=None):
        """  Returns target directories for mirroring eggs.

             Parameters
             ----------
             file_root : `path.path`
                 path to the root of the file store
             target_root : `path.path`
                 filesystem path to mirror to on target host
             target_packages : `list` or None
                 list of packages to mirror. Use None for all.
        """
        pkg_dirs = []
        [pkg_dirs.extend(letter.dirs()) for letter in file_root.dirs()]
        if target_packages:
            pkg_dirs = [i for i in pkg_dirs if i.basename() in target_packages]

        target_dirs = [target_root / self.get_mirror_dirname(i.basename())  \
                       for i in pkg_dirs]

        return pkg_dirs, target_dirs

    def unpack_eggs(self, files, target_host, target_root):
        """ Unpacks all eggs on the target host and root
        """
        print "Unpacking eggs: %r" % files

        target_eggs = [target_root / self.get_mirror_dirname(f.parent.basename()) \
                       / f.name for f in files]
        cmd = """set -x
            for EGG in %s; do
                if [ -f $EGG ]; then
                    echo Unzipping $EGG
                    ZIPFILE=./.tmp.`basename $EGG`
                    mv $EGG $ZIPFILE &&  \
                    mkdir $EGG &&  \
                    unzip -q $ZIPFILE -d $EGG && \
                    rm $ZIPFILE &&  \
                    chmod -R 555 $EGG
                fi
            done""" % ' '.join(target_eggs)
        print "Running cmd on %s" % target_host
        print cmd
        run(['/usr/bin/ssh', target_host, cmd])

    def mirror_eggs(self, file_root, target_host, target_root, target_packages=None,
                    subprocesses=10):
        """  Mirrors egg files from this PyPi instance to a target host and path

             Parameters
             ----------
             file_root : `str`
                 filesystem path to the root of the file store
             target_host : `str`
                 host to mirror to
             target_root : `str`
                 filesystem path to mirror to on target host
             target_packages : `list` or None
                 list of packages to mirror. Use None for all.
             subprocesses : `int`
                 number of subprocesses to spawn when doing the mirror
        """
        from path import path
        file_root = path(file_root)
        target_root = path(target_root)

        pkg_dirs, target_dirs = self.get_mirror_targets(file_root, target_root, target_packages)

        print "Creating target root dirs"
        run(['/usr/bin/ssh', target_host, 'mkdir -p ' + ' '.join(target_dirs)])

        work = []
        for pkg in pkg_dirs:
            # Filter non-egg and dev packages out, as this is a site-packages mirror
            # which won't work with source packages.
            files = [i for i in pkg.files() if i.basename().endswith('egg') and not 'dev' in i.basename()]
            print "Found %s (%d files)" % (pkg.basename(), len(files))
            if files:
                cmd = ['/usr/bin/rsync', '-av', '--ignore-existing'] + [i.abspath().strip() for i in files] + \
                        [target_host + ':' + target_root / self.get_mirror_dirname(pkg.basename())]
                work.append(cmd)

        # Using multiprocessing here to multiplex the transfers
        if subprocesses > 1:
            pool = Pool(processes=subprocesses)
            pool.map(run, work)
        else:
            map(run, work)

        self.unpack_eggs(files, target_host, target_root)


class CluePyPiApi(PyPiAPI):
    """ ClueReleaseManager PyPI API object.
        Caching lookup of packages by name for their VCS uris.
    """
    def _pkg_home(self, pkg):
        """ Return a package's homepage
        """
        return '/'.join([self.uri, 'd', pkg])

    def scrape_pkg_uri(self, uri, pkg):
        """
        Scrape package metadata from PyPi when it's running
        as the Clue Release Manager.

        Parameters
        ----------
        uri : `str`
            URI to page containing package's homepage
        pkg : `str`
            Package name
        """
        # Example entry:
        #<div class="distro-block distro-metadata">
        #  <h4>Metadata</h4>
        #  <dl>
        #    <dt>Distro Index Owner:</dt>
        #    <dd>acmepypi</dd>
        #    <dt>Home Page:</dt>
        #    <dd><a href="http://mysvn/acme.helloworld">
        #           http://mysvn/acme.helloworld</a></dd>
        #  </dl>
        #</div>
        tree = ElementTree()
        try:
            tree.parse(urllib2.urlopen(uri))
        except urllib2.HTTPError, e:
            raise UserError("Can't find repository URL for package %s (%s). "
                            "Has it been registered in PyPi?" % (pkg, e))
        ns = _get_namespace(tree)

        # Grr py2.6 version of etree doesn't support xpath
        #metadata = tree.find('//div[@class="distro-block distro-metadata"]')
        for div in tree.getroot().find(ns + 'body').findall(ns + 'div'):
            if 'distro-metadata' in div.attrib['class']:
                is_next = False
                for item in div.getiterator('*'):
                    if item.tag == ns + 'dt' and item.text == 'Home Page:':
                        is_next = True
                        continue
                    if is_next and item.tag == ns + 'a':
                        return item.attrib['href']
                break
        raise UserError("Can't find repository URL for package %s. "
                        "Has it been registered in PyPi?" % pkg)

    def get_vcs_uri(self, pkg):
        """ Return the VCS uri for a given package.
        """
        # Don't use _cache.get because we always evaluate the second arg.
        if pkg not in self._cache:
            self._cache[pkg] = self.scrape_pkg_uri(self._pkg_home(pkg), pkg)
        return self._cache[pkg]

    def get_links(self, pkg_name):
        """ Return the simple page links
        """
        tree = ElementTree()
        try:
            tree.parse(urllib2.urlopen('%s/simple/%s' % (self.uri, pkg_name)))
        except (urllib2.HTTPError, exceptions.SyntaxError):
            return None

        ns = _get_namespace(tree)
        return tree.getroot().findall(ns + 'body/ul/li/a')

    @property
    def clone_type(self):
        """The type of PyPI server we are connected to."""
        return 'clue'


class ChishopPyPiApi(PyPiAPI):
    """ Chishop PyPI API object.
        Caching lookup of packages by name for their VCS uris.
    """
    def __init__(self, uri=None, username=None, password=None):
        super(ChishopPyPiApi, self).__init__(uri, username, password)
        uri = self.uri
        if not uri.endswith('/'):
            uri += '/'
        self.proxy = xmlrpclib.ServerProxy(uri)

    def get_package_metadata(self, package, version):
        pkg_info = self.proxy.release_data(package, version)
        return pkg_info

    def get_last_version(self, package, dev=False, strict=False):
        versions = self.get_available_versions(package, dev, strict)
        if not versions:
            return None
        return versions[0]

    def get_available_versions(self, package, dev=False, strict=False):
        """
        Parameters
        ----------
        package: `str`
            Package name
        dev: `bool`
            If set, will only return dev versions. Otherwise, return
            only released versions.
        strict: `bool`
            If set, matches dev versions strictly.
            Eg: 0.0.dev OK, 2.33.dev3 -not OK.
        """
        versions = set(self.proxy.package_releases(package) +
                       self.proxy.package_releases(package, True))
        if dev:
            fn = is_dev_version
            if strict:
                fn = is_strict_dev_version
            versions = [version for version in versions
                        if fn(version)]
        else:
            versions = [version for version in versions
                        if not is_dev_version(version)]

        # Sort versions with most recent version at index 0.
        versions = [PackageVersion(v) for v in versions]
        versions.sort(reverse=True)
        versions = [str(v) for v in versions]
        return versions

    def get_vcs_uri(self, pkg):
        """ Return the VCS uri for a given package.
        """
        # Don't use _cache.get because we always evaluate the second arg.
        if pkg not in self._cache:
            self._cache[pkg] = self._cache.get(pkg, self.get_package_homepage(self.uri, pkg))
        return self._cache[pkg]

    # XXX This is never called from anywhere, why is it here? 
    def get_package_homepage(self, uri, pkg):
        """Use the XML-RPC interface to query release metadata for a given package"""
        url = urlparse.urljoin(uri, '/')    # add trailing slash if it wasn't specified.
        client = xmlrpclib.ServerProxy(url)
        releases = client.package_releases(pkg)
        releases.extend(client.package_releases(pkg, True))  # True => "hidden releases"
        #TODO: investigate ordering of release versions so we always use release
        #TODO: data from the most recent one.
        releases.sort()
        for release in releases[::-1]:  # walk backward through releases
            release_data = client.release_data(pkg, release)
            home_page = release_data.get('home_page', '')
            if len(home_page) > 4:
                return home_page

        raise UserError("Can't find repository URL for package %s. "
                        "Has it been registered in PyPI?" % pkg)

    def get_links(self, pkg_name):
        """
        Return the simple page links.
        """
        tree = ElementTree()
        try:
            tree.parse(urllib2.urlopen('%s/simple/%s' % (self.uri, pkg_name)))
        except (urllib2.HTTPError, exceptions.SyntaxError):
            return None

        return tree.getroot().findall('body/a')

    @property
    def clone_type(self):
        """The type of PyPI server we are connected to."""
        return 'chishop'


def PyPi(uri=None, username=None, password=None):
    """
    Factory method to detect PyPI server implementation and provide the
    correct API object.

    """
    if not uri:
        uri = CONFIG.pypi_url
    if has_pypi_xmlrpc_interface(uri):
        return ChishopPyPiApi(uri, username, password)
    else:
        return CluePyPiApi(uri, username, password)
