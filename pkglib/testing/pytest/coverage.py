'''
Created on 16 Apr 2012

@author: eeaston
'''
from pkglib.cmdline import run
from pkglib import manage


def run_with_coverage(cmd, pytestconfig, coverage='coverage', cd=None, **kwargs):
    """
    Run a given command with coverage enabled. This won't make any sense
    if the command isn't a python script.

    This must be run within a pytest session that has been setup with
    the '--cov=xxx' options, and therefore requires the pytestconfig
    argument that can be retrieved from the standard pytest funcarg
    of the same name.

    Parameters
    ----------
    cmd: `List`
        Command to run
    pytestconfig: `pytest._config.Config`
        Pytest configuration object
    coverage: `str`
        Path to the coverage executable
    cd: `str`
        If not None, will change to this directory before running the cmd.
        This is the directory that the coverage files will be created in.
    kwargs: keyword arguments
        Any extra arguments to pass to `pkglib.cmdline.run`

    Returns
    -------
    `str` standard output

    Examples
    --------

    >>> def test_example(pytestconfig):
    ...   cmd = ['python','myscript.py']
    ...   run_with_coverage(cmd, pytestconfig)
    """
    if isinstance(cmd, str):
        cmd = [cmd]

    args = [coverage, 'run', '-p']
    if pytestconfig.option.cov_source:
        source_dirs = ",".join(pytestconfig.option.cov_source)
        args += ['--source=%s' % source_dirs]
    args += cmd
    if cd:
        with manage.chdir(cd):
            return run(args, **kwargs)
    return run(args, **kwargs)
