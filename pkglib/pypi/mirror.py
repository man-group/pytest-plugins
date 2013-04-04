"""  PyPi accessor module
"""
import os
import logging
import ConfigParser
from multiprocessing import Pool

from pkglib.cmdline import run


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
        [pkg_dirs.extend(letter.dirs()) for letter in file_root.dirs()]
        if target_packages:
            pkg_dirs = [i for i in pkg_dirs if i.basename() in target_packages]

        target_dirs = [target_root / self.get_mirror_dirname(i.basename())
                       for i in pkg_dirs]

        return pkg_dirs, target_dirs

    def unpack_eggs(self, files, target_host, target_root):
        """ Unpacks all eggs on the target host and root
        """
        print "Unpacking eggs: %r" % files

        target_eggs = [(target_root /
                        self.get_mirror_dirname(f.parent.basename()) / f.name)
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
        print "Running cmd on %s" % target_host
        print cmd
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
        from path import path
        file_root = path(file_root)
        target_root = path(target_root)

        pkg_dirs, target_dirs = self.get_mirror_targets(file_root, target_root,
                                                        target_packages)

        print "Creating target root dirs"
        run(['/usr/bin/ssh', target_host, 'mkdir -p ' + ' '.join(target_dirs)])

        work = []
        for pkg in pkg_dirs:
            # Filter non-egg and dev packages out, as this is a site-packages
            # mirror which won't work with source packages.
            files = [i for i in pkg.files()
                     if i.basename().endswith('egg')
                     and not 'dev' in i.basename()]
            print "Found %s (%d files)" % (pkg.basename(), len(files))
            if files:
                cmd = (['/usr/bin/rsync', '-av', '--ignore-existing'] +
                       [i.abspath().strip() for i in files] +
                       [target_host + ':' + target_root /
                        self.get_mirror_dirname(pkg.basename())]
                      )
                work.append(cmd)

        # Using multiprocessing here to multiplex the transfers
        if subprocesses > 1:
            pool = Pool(processes=subprocesses)
            pool.map(run, work)
        else:
            map(run, work)

        self.unpack_eggs(files, target_host, target_root)
