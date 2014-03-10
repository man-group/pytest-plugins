from mock import patch, Mock

from pkglib.scripts import plat as plat_module


class MyDep(object):
    def __init__(self, name, version):
        self.name = name
        self.version = version


def test_info_command_pkg_info():
    with patch('pkglib.scripts.plat.statusmsg') as statusmsg:
        plat = Mock()
        info = (('p4', {'version': 'p4_version'}),
                ('p2', {'version': 'p2_version'}))
        source_checkouts = []
        plat.get_packages_information.return_value = (info, source_checkouts)
        plat_module.info_command(plat, 'anything')
        a = statusmsg.call_args_list
        assert len(a) == 2
        assert a[0] == (('p4: p4_version',), {})
        assert a[1] == (('p2: p2_version',), {})


def test_info_command_source_checkouts():
    with patch('pkglib.scripts.plat.statusmsg') as statusmsg:
        plat = Mock()
        info = []
        source_checkouts = [MyDep('bb', 'vbb'), MyDep('aa', 'vaa')]
        plat.get_packages_information.return_value = (info, source_checkouts)
        plat_module.info_command(plat, 'anything')
        a = statusmsg.call_args_list
        assert len(a) == 3
        assert a[0] == (('Other source checkouts:',), {})
        assert a[1] == (('    aa: vaa',), {})
        assert a[2] == (('    bb: vbb',), {})
