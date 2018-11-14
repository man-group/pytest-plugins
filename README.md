# A goody-bag of nifty plugins for [Py.Test](https://pytest.org)

[![Circle CI](https://circleci.com/gh/manahl/pytest-plugins.svg?style=shield)](https://circleci.com/gh/manahl/pytest-plugins)

[![Coverage Status](https://coveralls.io/repos/github/manahl/pytest-plugins/badge.svg?branch=master)](https://coveralls.io/github/manahl/pytest-plugins?branch=master)

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
| [pytest-git](pytest-git) | Git repository fixture | 
| [pytest-svn](pytest-svn) | SVN repository fixture | 
| [pytest-fixture-config](pytest-fixture-config) | Configuration tools for Py.test fixtures |
| [pytest-verbose-parametrize](pytest-verbose-parametrize) | Makes py.test's parametrize output a little more verbose |


## Developing these plugins

All of these plugins share setup code and configuration so there is a top-level Makefile to
automate process of setting them up for test and development.

### Pre-requisites

You have `python` installed on your path, preferably using a `virtualenv`

### Makefile targets

To install all dependencies and set up all of the packages for development simply run:

```bash
    make develop
```

To install all the packages as wheel distributions:

```bash
    make install
```

To run all the tests:

```bash
    make test
```

To setup test environment in Vagrant (requires virtualbox):

```bash
    $ vagrant up
    $ vagrant ssh

    # ..... inside vagrant ....
    . venv/bin/activate
    make develop
    export SELENIUM_BROWSER=phantomjs
    make test
```

## `foreach.sh` 

To run a command in each of the package directories, use the `foreach.sh` script.
This example will build all the wheel distributions:

```bash
    ./foreach.sh python setup.py bdist_wheel
```

