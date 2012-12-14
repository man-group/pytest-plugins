from pkglib.testing.util import TmpVirtualEnv, set_env, no_env



def test_PYTHONPATH_not_present_in_testing_env_if_set():
    with set_env('PYTHONPATH', 'fred'):
        with TmpVirtualEnv() as v:
            assert 'PYTHONPATH' not in v.env

        with TmpVirtualEnv({'PYTHONPATH': 'john'}) as v:
            assert 'PYTHONPATH' not in v.env


def test_PYTHONPATH_not_present_in_testing_env_if_unset():
    with no_env('PYTHONPATH'):
        with TmpVirtualEnv() as v:
            assert 'PYTHONPATH' not in v.env

        with TmpVirtualEnv({'PYTHONPATH': 'john'}) as v:
            assert 'PYTHONPATH' not in v.env


def check_member(name, ips):
    return name in ips

def test_installed_packages():
    with TmpVirtualEnv() as v:
        ips = v.installed_packages()
        assert len(ips) > 0
        check_member('distribute', ips)
        check_member('virtualenv', ips)
