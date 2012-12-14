"""
Provide some tests giving partial coverage of our extension.
"""


def test_ext_fn_1():
    from acme.foo import ext  # @UnresolvedImport
    assert ext.fn_1() == "fn_1"


def _skip_test_ext_fn_2():    # Skip testing fn_2 so we can check uncoverage
    from acme.foo import ext  # @UnresolvedImport
    assert ext.fn_2() == "fn_2"
