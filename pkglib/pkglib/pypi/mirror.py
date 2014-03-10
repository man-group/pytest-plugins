"""  PyPi accessor module
"""
import os
import logging
import ConfigParser
from multiprocessing import Pool

from pkglib_util.cmdline import run


def get_log():
    return logging.getLogger(__name__)


class EggMirrorMixin(object):
    """ Mixin to add egg mirroring functionality
    """
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
                keys = dev_server

                [dev_server]
                hostname = devbox1
                target_dir = /var/cache/eggs


            Returns
            -------
            mirrors : `list`
                List of ``{'target_host': hostname,
                           'target_dir', target file root
                          }``

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
        for root, dirs, _ in os.walk(file_root):
            if os.path.dirname(root) == file_root:
                pkg_dirs.extend([os.path.join(root, d) for d in dirs])
                dirs[:] = []  # prune dirs

        if target_packages:
            pkg_dirs = [i for i in pkg_dirs
                        if os.path.basename(i) in target_packages]

        target_dirs = [os.path.join(target_root, self.get_mirror_dirname(bn))
                       for bn in (os.path.basename(i) for i in pkg_dirs)]

        return pkg_dirs, target_dirs

    def unpack_eggs(self, files, target_host, target_root):
        """ Unpacks all eggs on the target host and root
        """
        print "Unpacking eggs: %r" % files

        target_eggs = [os.path.join(target_root, self.get_file_target(f))
                       for f in files]
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
        print("Running cmd on %s" % target_host)
        print(cmd)
        run(['/usr/bin/ssh', target_host, cmd])

    def mirror_eggs(self, file_root, target_host, target_root,
                    target_packages=None, subprocesses=10):
        """  Mirrors egg files from this PyPi instance to a target host and
             path. Used for filling out a cache that can be used by
             CONFIG.installer_search_path.

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
        pkg_dirs, target_dirs = self.get_mirror_targets(file_root,
                                                        target_root,
                                                        target_packages)

        work = []
        for pkg in pkg_dirs:
            # Filter non-egg and dev packages out, as this is a site-packages
            # mirror which won't work with source packages.
            files = [os.path.join(pkg, f) for f in os.listdir(pkg)
                     if os.path.isfile(os.path.join(pkg, f)) and
                     f.endswith('egg') and not 'dev' in f]
            print("Found %s (%d files)" % (os.path.basename(pkg), len(files)))
            if files:
                mirror_dir = self.get_mirror_dirname(os.path.basename(pkg))
                cmd = ['/usr/bin/rsync', '-av', '--ignore-existing']
                cmd.extend(os.path.abspath(i).strip() for i in files)
                cmd.append(os.path.join(target_host + ':' + target_root,
                                        mirror_dir))
                work.append(cmd)

        if work:
            print("Creating target root dirs")
            run(['/usr/bin/ssh', target_host,
                 'mkdir -p ' + ' '.join(target_dirs)])

            # Using multiprocessing here to multiplex the transfers
            if subprocesses > 1:
                pool = Pool(processes=subprocesses)
                pool.map(run, work)
            else:
                map(run, work)

            self.unpack_eggs(files, target_host, target_root)
        else:
            print("Nothing to do.")
