# Pytest GIT Fixture

Creates an empty Git repository for testing that cleans up after itself on teardown.

## Installation

Install using your favourite package installer:
```bash
    pip install pytest-git
    # or
    easy_install pytest-git
```
    
Enable the fixture explicitly in your tests or conftest.py (not required when using setuptools entry points):

```python
    pytest_plugins = ['pytest_git']
```

## Usage

This plugin is a thin wrapper around the excellent GitPython library (see http://gitpython.readthedocs.org/en/stable/).
Here's a noddy test case that shows it working:

```python
def test_git_repo(git_repo):
    # The fixture derives from `workspace` in `pytest-shutil`, so they contain 
    # a handle to the path.py path object (see https://pythonhosted.org/path.py)
    path = git_repo.workspace
    file = path / 'hello.txt'
    file.write_text('hello world!')
    
    # We can run commands relative to the working directory
    git_repo.run('git add hello.txt')
    
    # It's better to use the GitPython api directly - the 'api' attribute is 
    # a handle to the repository object.
    git_repo.api.index.commit("Initial commit")
    
    # The fixture has a URI property you can use in downstream systems
    assert git_repo.uri.startswith('file://')
```