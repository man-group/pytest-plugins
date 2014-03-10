import subprocess


def call(cmd, cwd=None):
    return subprocess.call(cmd.split(' '), cwd=cwd)


def popen(cmd, log_filename, cwd=None):
    return subprocess.Popen(cmd.split(' '),
                            stdout=open(log_filename, 'w', buffering=0),
                            stderr=subprocess.STDOUT, cwd=cwd)
