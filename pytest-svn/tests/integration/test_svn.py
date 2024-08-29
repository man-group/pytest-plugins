

def test_foo(svn_repo):
    assert hasattr(svn_repo, 'uri')
