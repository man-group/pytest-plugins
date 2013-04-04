import os.path

from pkglib.testing.util import Shell, Workspace, chdir


def test_Shell_func_1():
    with chdir(os.path.dirname(__file__)):
        with Shell('ls') as s:
            assert os.path.basename(__file__) in s.out.split('\n')


def test_Shell_func_1_as_list():
    with chdir(os.path.dirname(__file__)):
        with Shell(['ls']) as s:
            assert os.path.basename(__file__) in s.out.split('\n')


def test_Shell_func_2():
    this_dir = os.path.dirname(__file__)
    # start at parent of this directory
    with chdir(os.path.dirname(this_dir)):
        with Shell(['cd %s' % this_dir, 'ls']) as s:
            assert os.path.basename(__file__) in s.out.split('\n')


def test_adir_is_not_present_in_initial_state_ok():
    with Workspace() as w:
        # confirm that there is no adir directory
        with Shell(['cd %s' % w.workspace,
                                    'stat adir']
                                   ) as sh:
            sh.print_io()
            assert sh.err.strip().startswith("stat: cannot stat `adir':"), 'adir directory not absent!'


def test_mkdir_adir_stats_ok():
    with Workspace() as w:
        with Shell(['cd %s' % w.workspace,
                                    'mkdir adir',
                                    'stat adir']
                                   ) as sh:
            assert sh.out.strip().startswith('File: '), 'adir directory is absent'


def test_mkdir_adir_stats_abs_ok():
    with Workspace() as w:
        with Shell(['cd %s' % w.workspace,
                                    'mkdir adir',
                                    'stat %s/adir' % w.workspace]
                                   ) as sh:
            assert sh.out.strip().startswith('File: '), 'adir directory is absent'


def test_mkdir_with_abs_cd_works_ok():
    with Workspace() as w:
        with Shell(['cd %s' % w.workspace,
                                    'mkdir adir',
                                    'cd %s/adir' % w.workspace,
                                    'pwd'
                                   ]) as sh:

            assert sh.out.strip().endswith('/adir'), 'adir directory is absent'


def test_mkdir_with_relative_cd_ok():
    with Workspace() as w:
        with Shell(['cd %s' % w.workspace,
                    'mkdir adir',
                    'cd adir',
                    'pwd'
                     ]) as sh:
            sh.print_io()
            lines = sh.out.strip().split('\n')
            assert len(lines) == 1
            assert lines[0] == os.path.join(w.workspace, 'adir')


def test_shell_exception_ok():
    # TODO: this is brittle, diff output on diff OS
    with Shell(['junk_command']) as sh:
        assert 'not found' in sh.err.strip()
