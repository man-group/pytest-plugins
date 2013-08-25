PkgLib-Testing: Testing Tools for a Company-centric packaging library
=====================================================================

Kindly open-sourced by AHL, this library provides a suite of testing utilities 
to assist with handling services, databases, web drivers and coverage amongst 
other things, as well as a number of useful ``py.test`` plugins.
                      
Documentation
=============

There are the slides from my EuroPython 2013 talk up at 
http://github.com/eeaston/pkglib-docs, and the API docs are published at 
https://readthedocs.org/projects/pkglib-testing.
                          
Headline Features
=================

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
