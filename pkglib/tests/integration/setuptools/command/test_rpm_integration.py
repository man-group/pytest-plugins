from __future__ import print_function
import os

from pkglib_testing.util import PkgTemplate
from pkglib_testing.pytest.util import svn_repo, workspace  # @UnusedImport # NOQA

HERE = os.getcwd()


def test_rpm(svn_repo, workspace, pytestconfig):
    """ Creates template, runs setup.py egg_info which should then call
    rpm
    """
    cfg = dict(rpm=dict(services='svc1',
                        include_files='file1.txt\nfile2.txt',
                        install_requires='foo == 1\nbar <= 2'),
               svc1=dict(script='bin/svc1.sh',
                         env="FOO=1,BAR=2",
                         runas="myuser",
                         numprocs="2"),
               )

    with PkgTemplate(name='acme.foo', repo_base=svn_repo.uri, **cfg) as pkg:
        pkg.install_package('pytest-cov')
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            ("svn import %s/%s %s -m 'initial import'" %
             (pkg.workspace, 'acme.foo', pkg.vcs_uri)),
            'svn co %s/trunk %s/acme.foo' % (pkg.vcs_uri, workspace.workspace),
            'mkdir %s/acme.foo/bin' % workspace.workspace,
            'echo "echo foo" > %s/acme.foo/bin/svc1.sh' % workspace.workspace,
            'echo "test123" > %s/acme.foo/file1.txt' % workspace.workspace,
            'echo "test345" > %s/acme.foo/file2.txt' % workspace.workspace,
        ]]
        # Egg-info will trigger RPM
        print(pkg.run_with_coverage(['%s/acme.foo/setup.py' %
                                     workspace.workspace, 'egg_info'],
                                    pytestconfig, cd=HERE))
        egginfo_dir = workspace.workspace / 'acme.foo' / 'acme.foo.egg-info'

        ctl_dir = egginfo_dir / 'ctl'
        assert ctl_dir.isdir()

        file1 = ctl_dir / 'file1.txt'
        assert file1.isfile()
        assert file1.lines(retain=False) == ['test123']

        file2 = ctl_dir / 'file2.txt'
        assert file2.isfile()
        assert file2.lines(retain=False) == ['test345']

        script = ctl_dir / 'svc1.sh'
        assert script.isfile()
        assert script.lines(retain=False) == ['echo foo']

        ctl_file = ctl_dir / 'svc1.ctl'
        lines = ctl_file.lines(retain=False)
        assert 'PYRPM_SVC_ENVIRONMENT="FOO=1,BAR=2"' in lines
        assert 'PYRPM_SVC_NUMPROCS=2' in lines
        assert 'PYRPM_SVC_RUNAS="myuser"' in lines
        assert 'exec ${PYRPM_PKG_DIR}/ctl/svc1.sh ' in lines

        requires = egginfo_dir / 'rpm_requires.spec'
        assert requires.isfile()
        assert requires.lines(retain=False) == ['Requires: foo == 1, bar <= 2']
