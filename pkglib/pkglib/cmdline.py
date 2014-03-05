"""Cmdline tools utility module
"""
import logging
import getpass
import os
import shutil
import subprocess

from contextlib import contextmanager
from tempfile import mkdtemp

from distutils import log

try:  # Python 2
    str_type = basestring
except NameError:  # Python 3
    str_type = str


def get_log():
    return logging.getLogger(__name__)


@contextmanager
def umask(new_mask):
    """
    Context Manager to set the umask
    """
    try:
        old_mask = os.umask(new_mask)
        yield
    finally:
        os.umask(old_mask)


@contextmanager
def chdir(dirname):
    """
    Context Manager to change to a dir then change back
    """
    here = os.getcwd()
    try:
        os.chdir(dirname)
        yield
    finally:
        os.chdir(here)


@contextmanager
def set_home(dirname):
    """
    Context Mgr to set HOME
    """
    old_home = os.environ.get('HOME')
    try:
        os.environ['HOME'] = dirname
        yield
    finally:
        if old_home:
            os.environ['HOME'] = old_home


@contextmanager
def set_env(**kwargs):
    """
    Context Mgr to set HOME
    """
    old_env = dict(os.environ)
    try:
        for k, v in kwargs.items():
            if v is None:
                if k in os.environ:
                    del os.environ[k]
            else:
                os.environ[k] = v
        yield
    finally:
        if old_env:
            os.environ.clear()
            os.environ.update(old_env)


# TODO: add option to return results as a pipe to avoid buffering
#       large amounts of output
def run(cmd, stdin=None, capture_stdout=True, capture_stderr=False,
        check_rc=True, background=False, **kwargs):
    """
    Run a command; raises `subprocess.CalledProcessError` on failure.

    Parameters
    ----------
    stdin : file object
        text piped to standard input
    capture_stdout : `bool` or `stream`
        If set, stdout will be captured and returned
    capture_stderr : `bool`
        If set, stderr will be piped to stdout and returned
    **kwargs : optional arguments
        Other arguments are passed to Popen()
    """
    get_log().debug('exec: %s' % str(cmd))
    # Log to distutils here as well so we see it during setuptools stuff
    log.debug('exec: %s' % str(cmd))

    stdout = subprocess.PIPE if capture_stdout is True else capture_stdout if capture_stdout else None
    stderr = subprocess.STDOUT if capture_stderr else None
    stdin_arg = None if stdin is None else subprocess.PIPE

    p = subprocess.Popen(cmd, stdin=stdin_arg, stdout=stdout, stderr=stderr, **kwargs)

    if background:
        return p

    (out, _) = p.communicate(stdin)

    if out is not None and not isinstance(out, str_type):
        try:
            out = out.decode('utf-8')
        except:
            get_log().warn("Unable to decode command output to UTF-8")

    if check_rc and p.returncode != 0:
        err_msg = ((out if out else 'No output') if capture_stdout is True
                   else '<not captured>')
        cmd = cmd if isinstance(cmd, str) else ' '.join(cmd)
        get_log().error("Command failed: \"%s\"\n%s" % (cmd, err_msg.strip()))
        ex = subprocess.CalledProcessError(p.returncode, cmd)
        ex.output = err_msg
        raise ex

    return out


class PrettyFormatter(object):
    def __init__(self, color=True):
        from termcolor import colored
        self.color = color
        self.colored = colored
        self.buffer = []

    def hr(self):
        if self.color:
            self.buffer.append(self.colored("-" * 80, 'blue', attrs=['bold']))
        else:
            self.buffer.append("-" * 80)

    def title(self, txt):
        if self.color:
            self.buffer.append(self.colored("  %s" % txt, 'blue', attrs=['bold']))
        else:
            self.buffer.append("  %s" % txt)

    def p(self, txt, color, attrs=[]):
        if self.color:
            self.buffer.append(self.colored(txt, color, attrs=attrs))
        else:
            self.buffer.append(txt)

    def flush(self):
        print(self.__str__())
        self.buffer = []

    def __str__(self):
        return '\n'.join(self.buffer)


class TempDir(object):
    """Context manager for a temporary directory.

    Examples
    --------

    >>> import os
    >>> from pkgutils.cmdline import TempDir
    >>> with TempDir() as dir:
    ...   print(os.path.exists(dir))
    True
    >>> os.path.exists(dir)
    False
    """
    def __init__(self, delete=True, temp_dir=None, force_dir=None):
        self.delete = delete
        self.created = False

        if force_dir:
            if temp_dir:
                raise RuntimeError("Either `temp_dir` or `force_dir` can be provided, not both")

            self.dir = force_dir
        else:
            if temp_dir and not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            self.dir = mkdtemp(dir=temp_dir)
            self.created = True

        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
            self.created = True

        if self.created:
            get_log().info("Created tempdir at %s" % self.dir)

    def close(self):
        """Delete the directory"""
        if self.delete and self.dir is not None:
            try:
                get_log().info('Deleting %s' % self.dir)
                shutil.rmtree(self.dir)
            except Exception as e:
                get_log().error('could not delete %s - %s' % (self.dir, e[0]))
            finally:
                self.dir = None

    def __enter__(self):
        return self.dir

    def __exit__(self, *_):
        self.close()

    def __del__(self):
        self.close()


def copy_files(src, dest):
    """Copies files from one directory to another"""
    src_files = os.listdir(src)
    for file_name in src_files:
        full_file_name = os.path.join(src, file_name)
        if (os.path.isfile(full_file_name)):
            shutil.copy(full_file_name, dest)


class _Getch:
    """ Gets a single character from standard input.  Does not echo to the screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self):
        return self.impl()


class _GetchUnix:
    def __init__(self):
        import tty  # @UnusedImport # NOQA
        import sys  # @UnusedImport # NOQA

    def __call__(self):
        import sys
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows:
    def __init__(self):
        import msvcrt  # @UnusedImport # NOQA

    def __call__(self):
        import msvcrt
        return msvcrt.getch()  # @UndefinedVariable

getch = _Getch()


def request_username():
    """Prompt for user name"""
    default_user = getpass.getuser()
    username = raw_input('Username (default: %s): ' % default_user)
    if not username:
        username = default_user
    return username


def request_password():
    """Prompt for password"""
    password = ''
    while not password:
        password = getpass.getpass()
    return password


def wait_for_user_confirmation(text="Press ENTER to continue.."):
    getpass.getpass(text)


def which(name, flags=os.X_OK):
    """Analogue of unix 'which'. Borrowed from the Twisted project, see
       their licence here: https://twistedmatrix.com/trac/browser/trunk/LICENSE
    """
    result = []
    exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))
    path = os.environ.get('PATH', None)
    if path is None:
        return []
    for p in os.environ.get('PATH', '').split(os.pathsep):
        p = os.path.join(p, name)
        if os.access(p, flags):
            result.append(p)
        for e in exts:
            pext = p + e
            if os.access(pext, flags):
                result.append(pext)
    return result
