# Pytest SVN Fixture

Creates an empty SVN repository for testing that cleans up after itself on teardown.

## Installation

Install using your favourite package installer:
```bash
    pip install pytest-svn
    # or
    easy_install pytest-svn
```
    
Enable the fixture explicitly in your tests or conftest.py (not required when using setuptools entry points):

```python
    pytest_plugins = ['pytest_svn']
```

## Usage

Here's a noddy test case that shows it working:

```python
def test_svn_repo(svn_repo):
    # The fixture derives from `workspace` in `pytest-shutil`, so they contain 
    # a handle to the path.py path object (see https://pythonhosted.org/path.py)
    path = svn_repo.workspace
    file = path / 'hello.txt'
    file.write_text('hello world!')
    
    # We can also run things relative to the repo
    svn_repo.run('svn add hello.txt')
    
    # The fixture has a URI property you can use in downstream systems
    assert svn_repo.uri.startswith('file://')
```