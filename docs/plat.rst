.. _plat:

PkgLib - ``plat``
=======================

.. toctree::
   :maxdepth: 1

   autodoc/pkglib


Introduction
============

A *platform package* is a collection of python packages that are tested, released and installed as a single
unit. A python package that is part of a platform package is referred to as a *component* of the
platform.

We introduced the concept of platform packages to allow the management of interdependencies between
sets of python packages and alien (ie. non-python) packages in a controlled manner.

The ``plat`` tool is used to manage the installation of platform packages and to display information about
platform packages in a virtual environment.  The tool supports the installation of development packages,
fixing an environment at a specific release and automatically updating rolling releases that are referred
to as *current* releases.


Usage
=====

``plat [-h|--help] [-v|--verbose] command [-h|--help] [command-argument*]``

Commands
========

``plat list``
    Shows the available platform packages.
``plat info``
    Shows details of the platform packages that are active in the currently
    active virtualenv.
``plat components``
    Shows the components of a platform package.
``plat versions``
    Shows the versions of a platform package.
``plat use``
    Makes a platform package available in the currently active virtualenv.
``plat up``
    Updates platform packages that are installed in the currently active
    virtualenv.
``plat develop``
    Makes the source of a platform package or a component of a platform
    package available in the currently active virtualenv.
``plat undevelop``
    Removes sources of a platform package or a component of a platform
    package from the currently active virtualenv.


Optional parameters
===================

``-h, --help``
    Show this help message and exit. This argument can be specified as a global
    parameter or as a parameter to individual commands.
``-v, --verbose``
    Display verbose output.


Details
=======

``plat list``
-------------
Shows the available platform packages.

Usage:
::
    $ plat list

Example:
::
    $ plat list
    acme.lab: Acme Systems Lab
    
    

``plat info``
-------------
Shows details of the platform packages that are active in the currently active
virtualenv.

Usage:
::
    $ plat info

Example:
::
    $ plat info
    acme.lab: rel-current (1.9.12)


``plat components``
-------------------
Shows the components of a platform package.

Usage:
::
    $ plat components <package>

*package*
    A platform package.

Example:
::
    $ plat components acme.lab
    acme.lab (1.9.12): Acme Systems Lab
        acme.widgets (0.49.0)
        acme.crates (0.0.25)
        acme.databases (1.11.0)
        acme.webtools (0.0.14)
        acme.converters (0.26.0)


``plat versions``
-----------------
Shows the versions of a platform package.

Usage:
::
    $ plat versions <package>

*package*
    An installed platform package.

Example:
::
    $ plat versions acme.lab
    acme.lab: Acme Systems Lab
        1.4.0
        1.3.0
        1.2.0
        1.1.0
        1.0.0


``plat use``
------------
Makes a released platform package available in the currently active virtualenv.

Usage:
::
    $ plat use [<package>] [<version>]

*package*
    A platform package.
    
    Defaults to your organisation's configured default package.

*version*
    A version string.  Valid version strings are *rel-current* for the automatically
    updating, most up-to-date most up-to-date release, *dev* for the development
    release or a string in the format *rel-<number>* for a fixed release.

    Default is *rel-current*.

Examples:
::
    $ plat use acme.lab rel-current
    Using package acme.lab, version rel-current.

    $ plat use acme.lab rel-1.9.11
    Using package acme.lab, version rel-1.9.11.


``plat up``
-----------
Updates platform packages that are installed in the currently active
virtualenv.

Only platform packages on versions *rel-current* and *dev* are updated.

Usage:
::
    $ plat up

Example:
::
    $ plat up
    Updating package acme.lab. This might take some time.


``plat develop``
----------------
Makes the source of a platform package or a component of a platform
package available in the currently active virtualenv.

The platform package needs to be on version *dev*.

Usage:
::
    $ plat develop <package> <location>

*package*
    Package from which the source should be made available.  This should be either a
    platform- or component package.

*location*
    Optional location where the source should be stored.
    
    Default is to use the name of the package in the current directory.

Example:
::
    $ plat develop acme.widgets
    Updating package acme.lab. This might take some time.
    Develop package acme.widgets at /home/tsantego/src/acme.widgets


``plat undevelop``
------------------
Removes sources of a platform package or a component of a platform
package from the currently active virtualenv.

Usage:
::
    $ plat undevelop <package>

*package*
    Package of which the source is currently installed.  

Example:
::
    $ plat undevelop acme.widtets
    Undevelop package acme.widgets at /home/tsantego/src/acme.widgets
    Updating package acme.lab. This might take some time.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
