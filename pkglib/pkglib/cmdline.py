"""Cmdline tools utility module
"""
import logging
import subprocess
from distutils import log


def get_log():
    return logging.getLogger("pkglib.cmdline")

# TODO: add option to return results as a pipe to avoid buffering
#       large amounts of output


def run(cmd, stdin=None, capture_stdout=True, capture_stderr=False,
        check_rc=True, **kwargs):
    """
    Run a command; raises `subprocess.CalledProcessError` on failure.

    Parameters
    ----------
    stdin : file object
        text piped to standard input
    capture_stdout : `bool`
        If set, stdout will be captured and returned
    capture_stderr : `bool`
        If set, stderr will be piped to stdout and returned
    **kwargs : optional arguments
        Other arguments are passed to Popen()
    """
    get_log().debug('exec: %s' % str(cmd))
    # Log to distutils here as well so we see it during setuptools stuff
    log.debug('exec: %s' % str(cmd))

    stdout = stderr = None
    if capture_stdout:
        stdout = subprocess.PIPE
    if capture_stderr:
        stderr = subprocess.STDOUT

    p = subprocess.Popen(cmd, stdin=None if stdin is None else subprocess.PIPE, stdout=stdout,
                         stderr=stderr, **kwargs)

    (out, _) = p.communicate(stdin)
    if check_rc and p.returncode != 0:
        get_log().error(out)
        raise subprocess.CalledProcessError(p.returncode,
            cmd if isinstance(cmd, str) else ' '.join(cmd))
    return str(out)


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
        print self.__str__()
        self.buffer = []

    def __str__(self):
        return '\n'.join(self.buffer)
