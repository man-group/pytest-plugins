""" This patches the version parser to allow in-house build specifiers of
    third-party packages to be treated as released versions.

    Eg: foo-1.0         <- foo version 1.0
        foo-1.0_acme2   <- Acme Co's 2nd build of foo version 1.0
        foo-1.0_acme3   <- Acme Co's 3rd build of foo version 1.0

        foo-1.0 < foo-1.0_acme2 < foo-1.0_acme3
"""
import pkg_resources
import re

from pkglib import CONFIG

component_re = re.compile(r'(\d+ | [a-z]+ | \.| -)', re.VERBOSE)
replace = {'pre': 'c', 'preview': 'c', '-': 'final-', 'rc': 'c', 'dev': '@'}.get


def _parse_version_parts(s):
    for part in component_re.split(s):
        part = replace(part, part)
        if not part or part == '.':
            continue
        if part[:1] in '0123456789':
            yield part.zfill(8)    # pad for numeric comparison
        elif part == CONFIG.third_party_build_prefix:
            yield '*final'
            yield '!%s' % CONFIG.third_party_build_prefex
        else:
            yield '*' + part

    yield '*final'  # ensure that alpha/beta/candidate are before final

try:
    pkg_resources._parse_version_parts = _parse_version_parts
except:
    print("WARNING: Unable to patch pkg_resources._parse_version_parts")
    print("Using old distribute version?")