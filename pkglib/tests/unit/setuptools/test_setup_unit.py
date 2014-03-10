from mock import patch, Mock, sentinel

from pkglib.setuptools import setup as pkglib_setup

from .command.runner import TestCmd


def test_setup_parses_setup_cfg():
    with patch("pkglib.setuptools._setup.check_multiple_call"):
        with patch("pkglib.setuptools._setup.set_working_dir"):
            with patch("pkglib.config.get_pkg_cfg_parser") as get_cfg_parser:
                with patch("pkglib.config.parse_pkg_metadata") as parse_metadata:
                    parse_metadata.return_value = {'name': sentinel.name}
                    run = Mock()
                    with patch('sys.argv', ['setup.py', 'xx']):
                        with patch('distutils.log.info'):
                            pkglib_setup(cmdclass={'xx': type('MockCmd', (TestCmd,),
                                                                {'run': lambda self: run(self)})})
    parse_metadata.assert_called_with(get_cfg_parser.return_value)
    assert run.called
    assert run.call_args[0][0].distribution.metadata.name == sentinel.name


def test_setup_detects_double_call():
    with patch("pkglib.setuptools._setup.set_working_dir"):
        with patch("pkglib.config.get_pkg_cfg_parser"):
            with patch("pkglib.config.parse_pkg_metadata") as parse_metadata:
                parse_metadata.return_value = {'name': sentinel.name}
                with patch('sys.argv', ['setup.py', '--name']):
                    with patch('distutils.log.info'):
                        with patch('sys.stderr') as sys_stderr:
                            pkglib_setup()
                            with patch('sys.exit') as sys_exit:
                                pkglib_setup()
    assert ('setup() has already been run! setup.py should only call setup() once.' in
            '\n'.join(s for a, _ in sys_stderr.write.call_args_list for s in a))
    sys_exit.assert_called_with(1)
