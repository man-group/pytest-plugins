""" PkgLib organisation configuration
"""
import io
import ConfigParser
import os.path
import distutils


import pkglib.config
import pkglib.errors


class TestingConfig(pkglib.config.Config):
    __slots__ = ('java_executable', 'jenkins_war', 'mongo_bin', 'redis_executable')


def setup_testing_config(from_string=None, from_file=None, from_env="PKGLIB_CONFIG"):
    """
    Sets up the PkgLib-Testing global configuration.

    Parameters
    ----------
    from_string : `str`
        Reads from a string.
    from_file : `str`
        Reads from a file
    from_env : `str`
        Reads from a file nominated by ``from_env``.

    """
    p = ConfigParser.ConfigParser()
    if from_string:
        p.readfp(io.BytesIO(from_string))
    elif from_file:
        p.read(from_file)
    else:
        if not from_env in os.environ:
            distutils.log.warn("Can't configure PkgLib, missing environment "
                               "variable {0}".format(from_env))
            return
        if not os.path.isfile(os.environ[from_env]):
            raise pkglib.errors.UserError(
                    "Can't configure PkgLib, unable to read config at {0}"
                    .format(os.environ[from_env]))
        p.read(os.environ[from_env])

    import pkglib_testing
    pkglib.config.set_config(pkglib_testing.CONFIG,
                             pkglib.config._parse_metadata(p, 'pkglib_testing', []))