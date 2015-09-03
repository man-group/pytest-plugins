from pytest_virtualenv import PackageEntry


def test_issrc_dev_in_version_plus_path_to_source_True():
    p = PackageEntry('acme.x', '1.3.10dev1', 'path/to/source')
    assert p.issrc


def test_issrc_no_dev_in_version_plus_path_to_source_False():
    p = PackageEntry('acme.x', '1.3.10', 'path/to/source')
    assert not p.issrc


def test_isdev_path_to_source_blank_string_True():
    p = PackageEntry('acme.x', '1.3.10dev1', '')
    assert p.isdev


def test_issrc_path_to_source_None_False():
    p = PackageEntry('acme.x', '1.3.10dev1', None)
    assert not p.issrc


def test_isdev_dev_in_version_plus_path_to_source_False():  # issrc case
    p = PackageEntry('acme.x', '1.3.10dev1', 'anything')
    assert not p.isdev


def test_isdev_dev_in_version_path_to_source_None_True():
    p = PackageEntry('acme.x', '1.3.10dev1', None)
    assert p.isdev


def test_isdev_no_dev_in_version_path_to_source_None_False():
    p = PackageEntry('acme.x', '1.3.10', None)
    assert not p.isdev


def test_isrel_no_dev_in_version_path_to_source_None_True():
    p = PackageEntry('acme.x', '1.3.10', None)
    assert p.isrel


def test_isrel_no_dev_in_version_plus_path_to_source_True():
    p = PackageEntry('acme.x', '1.3.10', 'anything')
    assert p.isrel


def test_isrel_no_dev_in_version_plus_path_to_source_None_False():
    p = PackageEntry('acme.x', '1.3.10dev1', None)
    assert not p.isrel


def test_match_dev_ok():
    pe = PackageEntry('acme.x', '1.3.10dev1', None)
    assert pe.match(PackageEntry.ANY)
    assert pe.match(PackageEntry.DEV)
    assert not pe.match(PackageEntry.SRC)
    assert not pe.match(PackageEntry.REL)


def test_match_source_ok():
    pe = PackageEntry('acme.x', '1.3.10dev1', 'path/to/source')
    assert pe.match(PackageEntry.ANY)
    assert not pe.match(PackageEntry.DEV)
    assert pe.match(PackageEntry.SRC)


def test_match_rel_ok():
    pe = PackageEntry('acme.x', '1.3.10', None)
    assert pe.match(PackageEntry.ANY)
    assert not pe.match(PackageEntry.DEV)
    assert not pe.match(PackageEntry.SRC)
    assert pe.match(PackageEntry.REL)
