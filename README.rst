PkgLib: Company-centric Python packaging and testing library
============================================================

Kindly open-sourced by AHL, this library has the goal of providing a 
one-stop-shop for Python development houses to get up and running using Python 
with the minimum of fuss in a Linux development environment.

This library has three main components: 

- ``pkglib``: a set of packaging tools which extend on a number of the major 
  packaging toolsets in Python - distribute, pip and zc.buildout.
              
- ``pkglib.testing``: a suite of testing utilities to assist with handling 
  services, databases, web drivers and coverage amongst other things, as well 
  as a number of useful ``py.test`` plugins.
                      
- ``pkglib.project_template``: a PasteScript template for generating packages 
  that integrate with ``pkglib``


Documentation
=============

There are the slides from my EuroPython 2013 talk up at 
http://github.com/eeaston/pkglib-docs, and the API docs are published at 
https://readthedocs.org/projects/pkglib.
                          
Headline Features
=================

PkgLib
------

- Package metadata all sourced from text-file ``setup.cfg``, making it easier 
  to parse package configuration by other releated tools.
  
- Advanced dependency management:

  + Allows configuration of in-house company packages that are treated 
    differently than third-party libraries.
  + Backtracking dependency resolver to solve the difficult 'diamond problem' 
    of version resolution in complex dependency graphs.
  + Understands 'dev' and 'release' version streams, allowing the user to 
    operate in either mode. 
  + Tools to visualise dependency graphs from your current virtualenv.

- Improved PyPI interaction, prompts for user credentials and raises correct 
  Unix return codes on error.
  
- Installer search path support to allow eggs to be linked into virtualenvs 
  from shared disk, an important feature when working on shared filesystems in 
  large teams.  
  
- Keeps things neat and tidy - cleans out unused packages from your virtualenv's 
  site-packages directory. 
  
- Py.Test integration with ``python setup.py test``:

  + Configured for sensible defaults for code coverage and quality analysis
  + Detects when running under Jenkins and Hudson, swapping to file-based 
    reporting and altering tempfile creation.
    
- Command-line tool for managing software 'platforms', an abstraction upon 
  single packages when large numbers of interdependant packages are released 
  together.

- Checkout and setup packages from in-house repositories by name rather than 
  url.
   
- Numerous powerful ``setup.py`` targets:

  + Combine standalone package docs with automatic API documentation using 
    Sphinx.
  + Run tests using gcov to allow gathering code coverage of C/C++ extensions.
  + Synchronise checkouts and libraries with VCS and PyPI
  + Create Jenkins/Hudson builds.
  + Generate revision-linked development eggs for build systems.
  + Generate test-only eggs to capture test code and runtime options.
  + Deploy package to versioned virtualenvs.

- 'Batteries Included' project template


PkgLib.Testing
--------------

- Utilities with associated Py.Test fixture plugins for:

  + Profiling code execution, including C/C++ extensions
  + Managing temp dirs
  + Creating virutalenvs
  + Creating ``pkglib`` enabled packages
  + Running up servers instances in a port-safe manner, with save, restore and 
    teardown.
  + Supported servers include jenkins, redis, mongodb, Pyramid and (TODO) a 
    minimal PyPI implementation.
  + Selenium Webdriver, integrated with the Pyramid server runner plugin.
- Page Objects pattern implementation for better structured Selenium tests.
- Mocking implementations for databases and other common types.


Roadmap
=======

* Full support for git and mercurial.
* OSX support
* Python 2.4 -> 3.x support for core distlib functionality.
* Upgrade to latest versions of distribute, and bring the project in-line with 
  recent developements in the Python packaging space like ``distlib``.
* Add support for wheel binary distribution format.

                        
Contributors
============

- Edward Easton (eeaston@gmail.com)
- David Moss (drkjam@gmail.com)
- Terry Santegoeds
- Ed Catmur (ed@catmur.co.uk)
- Ben Walsh
- Tim Couper (drtimcouper@gmail.com)
- Inti Ocean (me@inti.co)
- Andrew Burrows
- James Blackburn
- Stepan Kolesnik (wigbam@yahoo.co.uk)
- Oisin Mulvihill (oisin.mulvihill@gmail.com)

