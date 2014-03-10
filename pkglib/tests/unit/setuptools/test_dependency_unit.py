'''
Created on 15 May 2012

@author: eeaston
'''
import pytest
import pkg_resources

from pkg_resources import WorkingSet
parse_req = pkg_resources.Requirement.parse

from pkglib.setuptools import dependency

from .command.runner import create_dist


@pytest.mark.parametrize(
    ("req", 'exp_lower', 'exp_upper', 'exp_lower_closed', 'exp_upper_closed'),
    [('foo', '0', '99999999', True, True),
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
    ('foo[a]>1', 'foo<=3', 'foo[a]>1,<=3'),
    ('foo[a]>1', 'foo[b,c]<=3', 'foo[a,b,c]>1,<=3'),
    ('foo>1', 'foo[b]<=3', 'foo[b]>1,<=3'),
])
def test_merge_requirements(r1, r2, exp):
    req1, req2 = pkg_resources.parse_requirements((r1, r2))
    if isinstance(exp, type) and Exception in exp.__bases__:
        with pytest.raises(exp):
            dependency.merge_requirements(req1, req2)
    else:
        assert dependency.merge_requirements(req1, req2).hashCmp == parse_req(exp).hashCmp


def test_remove_from_ws__removes_distribution():
    ws = WorkingSet([])
    dist = create_dist("a", "1.0")

    assert dist not in ws

    ws.add(dist)
    assert dist in ws

    dependency.remove_from_ws(ws, dist)
    assert dist not in ws


def test_remove_from_ws__removes_all_entries():
    ws = WorkingSet([])
    dist1 = create_dist("a", "1.0", location="a10")
    dist2 = create_dist("a", "2.0", location="a20")

    assert dist1 not in ws
    assert dist2 not in ws

    ws.add(dist1)
    assert dist1 in ws
    assert dist1.location in ws.entries
    assert dist2 not in ws
    assert dist2.location not in ws.entries

    ws.add_entry(dist2.location)
    assert dist1 in ws
    assert dist1.location in ws.entries
    assert dist2 not in ws
    assert dist2.location in ws.entries

    dependency.remove_from_ws(ws, dist2)

    assert dist1 not in ws
    assert dist2 not in ws

    assert len([d for d in ws]) == 0
