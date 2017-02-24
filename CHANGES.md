
## Changelog

### 1.2.10 (2017-2-23)
 * Handle custom Pytest test items in pytest-webdriver

### 1.2.9 (2017-2-23)
 * Add username into mongo server fixture tempdir path to stop collisions on shared multiuser filesystems

### 1.2.8 (2017-2-21)
 * Return function results in shutil.run.run_as_main

### 1.2.7 (2017-2-20)
 * More handling for older versions of path.py
 * Allow virtualenv argument passing in pytest-virtualenv

### 1.2.6 (2017-2-16 )
 * Updated devpi server server setup for devpi-server >= 2.0
 * Improvements for random port picking
 * HTTPD server now binds to 0.0.0.0 by default to aid Selenium-style testing
 * Updated mongodb server args for mongodb >= 3.2
 * Corrections for mongodb fixture config and improve startup logic
 * Added module-scoped mongodb fixture
 * Handling for older versions of path.py
 * Fix for #40 where tests that chdir break pytest-profiling

### 1.2.5 (2016-12-09)
 * Improvements for server runner host and port generation, now supports random local IPs
 * Bugfix for RethinkDB fixture config

### 1.2.4 (2016-11-14)
 * Bugfix for pymongo extra dependency
 * Windows compatibility fix for pytest-virtualenv (Thanks to Jean-Christophe Fillion-Robin for PR)
 * Fix symlink handling for pytest-shutil.cmdline.get_real_python_executable

### 1.2.3 (2016-11-7)
 * Improve resiliency of Mongo fixture startup checks

### 1.2.2 (2016-10-27)
 * Python 3 compatibility across most of the modules
 * Fixed deprecated Path.py imports (Thanks to Bryan Moscon)
 * Fixed deprecated multicall in pytest-profiling (Thanks to Paul van der Linden for PR)
 * Added devpi-server fixture to create an index per test function
 * Added missing licence file
 * Split up httpd server fixture config so child classes can override loaded modules easier
 * Added 'preserve_sys_path' argument to TestServer base class which exports the current python sys.path to subprocesses. 
 * Updated httpd, redis and jenkins runtime args and paths to current Ubuntu spec
 * Ignore errors when tearing down workspaces to avoid race conditions in 'shutil.rmtree' implementation

### 1.2.1 (2016-3-1)
 * Fixed pytest-verbose-parametrize for latest version of py.test

### 1.2.0 (2016-2-19)
 * New plugin: git repository fixture

### 1.1.1 (2016-2-16)
 * pytest-profiling improvement: escape illegal characters in .prof files (Thanks to Aarni Koskela for the PR)

### 1.1.0 (2016-2-15)
 
 * New plugin: devpi server fixture
 * pytest-profiling improvement: overly-long .prof files are saved as the short hash of the test name (Thanks to Vladimir Lagunov for PR)
 * Changed default behavior of workspace.run() to not use a subshell for security reasons
 * Corrected virtualenv.run() method to handle arguments the same as the parent method workspace.run()
 * Removed deprecated '--distribute' from virtualenv args

### 1.0.1 (2015-12-23)

 *  Packaging bugfix

### 1.0.0 (2015-12-21)

 *  Initial public release

