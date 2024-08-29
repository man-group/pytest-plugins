# A goody-bag of nifty plugins for [pytest](https://pytest.org)

OS | Build | Coverage |
 ------  | ----- | -------- |
 ![Linux](img/linux.png) | [![CircleCI (Linux)](https://circleci.com/gh/man-group/pytest-plugins/tree/master.svg?style=svg)](https://circleci.com/gh/man-group/pytest-plugins/tree/master) | [![Coverage Status](https://coveralls.io/repos/github/manahl/pytest-plugins/badge.svg?branch=master)](https://coveralls.io/github/manahl/pytest-plugins?branch=master)
 ![Windows](img/windows.png) | [![Travic CI (Windows)](https://travis-ci.org/man-group/pytest-plugins.svg?branch=master)](https://travis-ci.org/man-group/pytest-plugins) |

Plugin | Description | Supported OS |
------ | ----------- | ------------ |
| [pytest-server-fixtures](pytest-server-fixtures) |  Extensible server-running framework with a suite of well-known databases and webservices included | ![Linux](img/linux.png)
| [pytest-shutil](pytest-shutil) | Unix shell and environment management tools |![Linux](img/linux.png)
| [pytest-profiling](pytest-profiling) | Profiling plugin with tabular heat graph output and gprof support for C-Extensions |![Linux](img/linux.png)
| [pytest-devpi-server](pytest-devpi-server) | DevPI server fixture |![Linux](img/linux.png)
| [pytest-pyramid-server](pytest-pyramid-server) | Pyramid server fixture |![Linux](img/linux.png)
| [pytest-webdriver](pytest-webdriver) | Selenium webdriver fixture |![Linux](img/linux.png)
| [pytest-virtualenv](pytest-virtualenv) | Virtualenv fixture |![Linux](img/linux.png) ![Windows](img/windows.png)
| [pytest-qt-app](pytest-qt-app) | PyQT application fixture |![Linux](img/linux.png)
| [pytest-listener](pytest-listener)  | TCP Listener/Reciever for testing remote systems |![Linux](img/linux.png) ![Windows](img/windows.png)
| [pytest-git](pytest-git) | Git repository fixture |![Linux](img/linux.png) ![Windows](img/windows.png)
| [pytest-svn](pytest-svn) | SVN repository fixture |![Linux](img/linux.png)
| [pytest-fixture-config](pytest-fixture-config) | Configuration tools for Py.test fixtures |![Linux](img/linux.png) ![Windows](img/windows.png)
| [pytest-verbose-parametrize](pytest-verbose-parametrize) | Makes py.test's parametrize output a little more verbose |![Linux](img/linux.png)


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

## Vagrant

Some of the plugins have complex dependencies, particularly `pytest-server-fixtures`.
To make it easier to develop, there is a `Vagrantfile` which will setup a virtual machine
with all the dependencies installed to run the tests.

To set up the environment in Vagrant (requires virtualbox) and run the tests:

```bash
    $ vagrant up
    $ vagrant ssh

    # ..... inside vagrant ....
    . venv/bin/activate
    cd src
    make develop
    make test
```

## `foreach.sh`

To run a command in each of the package directories, use the `foreach.sh` script.
This example will build all the wheel distributions:

```bash
    ./foreach.sh python setup.py bdist_wheel
```

### Only-Changed mode

To run a command only on packages that have changed since the last tagged release, use `--changed`.
This example will only upload packages that need releasing:

```bash
    ./foreach.sh python setup.py bdist_wheel upload
```

### Quiet mode

To run a command with no extra output other than from what you run, use `--quiet`
```bash
    ./foreach.sh --quiet grep PY3
```


