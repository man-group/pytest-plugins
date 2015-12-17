# Pytest Verbose Parametrize

Pytest parametrize hook to generate ids for parametrized tests that are a little
more descriptive than the default (which just outputs id numbers).

## Installation

Install with your favourite package manager, and this plugin will automatically be enabled:
```bash
pip install pytest-verbose-parametrize
# or .. 
easy_install pytest-verbose-parametrize
```
## Usage

```python
import pytest

@pytest.mark.parametrize(('f', 't'), [(sum, list), (len, int)])
def test_foo(f, t):
    assert isinstance(f([[1], [2]]), t)
```

In this example, the test ids will be generated as `test_foo[sum-list]`,
`test_foo[len-int]` instead of the default `test_foo[1-2]`, `test_foo[3-4]`.

```bash
$ py.test -v 
============================= test session starts ======================================
platform linux2 -- Python 2.7.3 -- py-1.4.25 -- pytest-2.6.4 
plugins: verbose-parametrize
collected 2 items 

unit/test_example.py::test_foo[sum-list] FAILED
unit/test_example.py::test_foo[len-int] PASSED
```

