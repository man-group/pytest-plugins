# A goody-bag of nifty plugins for [Py.Test](https://pytest.org)

Plugin | Description |
------ | ----------- |
| [pytest-server-fixtures](pytest-server-fixtures) |  Extensible server-running framework with a suite of well-known databases and webservices included | 
| [pytest-shutil](pytest-shutil) | Unix shell and environment management tools |
| [pytest-profiling](pytest-profiling) | Profiling plugin with tabular heat graph output and gprof support for C-Extensions | 
| [pytest-devpi-server](pytest-devpi-server) | DevPI server fixture | 
| [pytest-pyramid-server](pytest-pyramid-server) | Pyramid server fixture | 
| [pytest-webdriver](pytest-webdriver) | Selenium webdriver fixture | 
| [pytest-virtualenv](pytest-virtualenv) | Virtualenv fixture | 
| [pytest-qt-app](pytest-qt-app) | PyQT application fixture | 
| [pytest-listener](pytest-listener)  | TCP Listener/Reciever for testing remote systems | 
| [pytest-svn](pytest-svn) | SVN repository fixture | 
| [pytest-fixture-config](pytest-fixture-config) | Configuration tools for Py.test fixtures |
| [pytest-verbose-parametrize](pytest-verbose-parametrize) | Makes py.test's parametrize output a little more verbose |


## Developing these plugins

All of these plugins share setup code and configuration so there is a top-level Makefile to
automate process of setting them up for test and development.

### Pre-requisites

You have `python` installed on your path as well as `virtualenv`

### Makefile targets

To create a local virtualenv called `venv`, install all extra dependencies and set up all
of the packages for development simply run:

```bash
    make develop
```

To do this for a subset of packages run:

```bash
    make develop PACKAGES="pytest-profiling pytest-devpi"
```

If you already have a virtualenv and would rather just use that, you can run this to 
copy all the required files in place so you can do your own setup:

```bash
    make copyfiles
    # Now you can do your own setup
    cd pytest-shutil
    python setup.py develop
```
