'''
Created on 15 May 2012

@author: eeaston
'''
import pytest
import pkg_resources

from pkglib.setuptools import dependency


def parse_req(req):
    # sometimes i really hate generators
    return [i for i in pkg_resources.parse_requirements([req])][0]


@pytest.mark.parametrize(("req", 'exp_lower', 'exp_upper', 'exp_lower_closed',
                          'exp_upper_closed'), [
    ('foo', '0', '99999999', True, True),
    ('foo==1.2', '1.2', '1.2', True, True),
    ('foo>1.0', '1.0', '99999999', False, True),
    ('foo<2.0', '0', '2.0', True, False),
    ('foo>1.0,<=2.0', '1.0', '2.0', False, True),
    ('foo>=1.0,>1.0', '1.0', '99999999', False, True),
])
def test_get_bounds(req, exp_lower, exp_upper, exp_lower_closed, exp_upper_closed):
    assert dependency.get_bounds(parse_req(req)) == \
        (exp_lower, exp_upper, exp_lower_closed, exp_upper_closed)


@pytest.mark.parametrize(("r1", 'r2', 'exp'), [
    ('foo==1', 'foo', 'foo==1'),
    ('foo==2', 'foo>=1', 'foo==2'),
    ('foo==2', 'foo>2', dependency.CannotMergeError),
    ('foo==1', 'foo==2', dependency.CannotMergeError),
    ('foo==1', 'foo==1', 'foo==1'),
    ('foo', 'foo', 'foo'),
    ('foo', 'foo>2', 'foo>2'),
    ('foo', 'bar', dependency.CannotMergeError),
    ('foo>=1', 'foo>1', 'foo>1'),
    ('foo>=1', 'foo<=3', 'foo>=1,<=3'),
    ('foo>1', 'foo<=3', 'foo>1,<=3'),
])
def test_merge_requirements(r1, r2, exp):
    req1, req2 = pkg_resources.parse_requirements((r1, r2))
    if isinstance(exp, type) and Exception in exp.__bases__:
        with pytest.raises(exp):
            dependency.merge_requirements(req1, req2)
    else:
        assert dependency.merge_requirements(req1, req2).hashCmp == parse_req(exp).hashCmp
