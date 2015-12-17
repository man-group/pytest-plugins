# Py.test Virtualenv Fixture

Create a Python virtual environment in your test that cleans up on teardown. 
The fixture has utility methods to install packages and list what's installed.

## Installation

Install using your favourite package installer:
```bash
    pip install pytest-virtualenv
    # or
    easy_install pytest-virtualenv
```
    
Enable the fixture explicitly in your tests or conftest.py (not required when using setuptools entry points):

```python
    pytest_plugins = ['pytest_virtualenv']
```

## Configuration

This fixture is configured using the following evironment variables

| Setting | Description | Default
| ------- | ----------- | -------
| VIRTUALENV_FIXTURE_EXECUTABLE | Which virtualenv executable will be used to create new venvs | `virtualenv`


## Fixture Attributes

Here's a noddy test case to demonstrate the basic fixture attributes. 
For more information on `path.py` see https://pythonhosted.org/path.py

```python
def test_virtualenv(virtualenv):
    # the 'virtualenv' attribute is a `path.py` object for the root of the virtualenv
    dirnames = virtualenv.virtualenv.dirs()
    assert {'bin', 'include', 'lib'}.intersection(set(dirnames))
    
    # the 'python' attribute is a `path.py` object for the python executable
    assert virtualenv.python.endswith('/bin/python')
```

## Installing Packages

You can install packages by name and query what's installed.

```python
def test_installing(virtualenv):
    virtualenv.install_package('coverage', installer='pip')
    
    # installed_packages() will return a list of `PackageEntry` objects.
    assert 'coverage' in [i.name for i in virtualenv.installed_packages()]
```

## Developing Source Checkouts

Any packages set up in the *test runner's* python environment (ie, the same runtime that 
``py.test`` is installed in) as source checkouts using `python setup.py develop` will be 
detected as such and can be installed by name using `install_package`.
By default they are installed into the virtualenv using `python setup.py develop`, there
is an option to build and install an egg as well:

```python
def test_installing_source(virtualenv):
    # Install a source checkout of my_package as an egg file
    virtualenv.install_package('my_package',  build_egg=True)
```


## Running Commands

The test fixture has a `run` method which allows you to run commands with the correct
paths set up as if you had activated the virtualenv first. 

```python
def test_run(virtualenv):
    python_exe_path  = virtualenv.python
    runtime_exe = virtualenv.run("python -c 'import sys; print sys.executable'", capture=True)
    assert runtime_exe == python_exe_path
```

## Running Commands With Coverage

The test fixture has a `run_with_coverage` method which is like `run` but runs the command
under coverage *inside the virtualenv*. This is useful for capturing test coverage on 
tools that are being tested outside the normal test runner environment.

```python
def test_coverage(virtualenv):
    # You will have to install coverage first
    virtualenv.install_package(coverage)
    virtualenv.run_with_coverage(["my_entry_point", "--arg1", "--arg2"])
```