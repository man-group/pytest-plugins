
## Changelog

### 1.6.2 (Unreleased)
 * pytest-server-fixtures: suppress stacktrace if kill() is called
 * pytest-server-fixtures: fix random port logic in TestServerV2

### 1.6.1 (2019-02-12)
 * pytest-server-fixtures: fix exception when attempting to access hostname while server is not started

### 1.6.0 (2019-02-12)
 * pytest-server-fixtures: added previously removed TestServerV2.kill() function
 * pytest-profiling: pin more-itertools==5.0.0 in integration tests, as that's a PY3 only release

### 1.5.1 (2019-01-24)
 * pytest-verbose-parametrize: fixed unicode parameters when using `@pytest.mark.parametrize`

### 1.5.0 (2019-01-23)
 * pytest-server-fixtures: made postgres fixtures and its tests optional, like all other fixtures
 * pytest-server-fixtures: reverted a fix for pymongo deprecation warning, as this will break compatibility with pymongo 3.6.0
 * pytest-server-fixtures: dropped RHEL5 support in httpd

### 1.4.1 (2019-01-18)
 * pytest-server-fixtures: server fixture binary path specified in ENV now only affect server class 'thread'

### 1.4.0 (2019-01-15)
 * Fixing python 3 compatibility in Simple HTTP Server fixture
 * Fixed broken tests in pytest-profiling
 * Pinned pytest<4.0.0 until all deprecation warnings are fixed.
 * pytest-webdriver: replaced deprecated phantomjs with headless Google Chrome.
 * Add Vagrantfile to project to make test environment portable.
 * Add .editorconfig file to project.
 * pytest-server-fixtures: add TestServerV2 with Docker and Kubernetes support.
 * pytest-server-fixtures: fix for an issue where MinioServer is not cleaned up after use.
 * pytest-server-fixtures: fix deprecation warnings when calling pymongo.
 * pytest-server-fixtures: close pymongo client on MongoTestServer teardown.
 * pytest-server-fixtures: upgrade Mongo, Redis and RethinkDB to TestServerV2.
 * coveralls: fix broken coveralls

### 1.3.1 (2018-06-28)
 * Use pymongo list_database_names() instead of the deprecated database_names(), added pymongo>=3.6.0 dependency

### 1.3.0 (2017-11-17)
 * Fixed workspace deletion when teardown is None
 * Fixed squash of root logger in pytest-listener
 * Added S3 Minio fixture (many thanks to Gavin Bisesi)
 * Added Postgres fixture (many thanks to Gavin Bisesi)
 * Use requests for server fixtures http gets as it handles redirects and proxies properly

### 1.2.12 (2017-8-1)
 * Fixed regression on cacheing ephemeral hostname, some clients were relying on this. This is now optional.

### 1.2.11 (2017-7-21)
 * Fix for OSX binding to illegal local IP range (Thanks to Gavin Bisesi)
 * Setup and Py3k fixes for pytest-profiling (Thanks to xoviat)
 * We no longer try and bind port 5000 when reserving a local IP host, as someone could have bound it to 0.0.0.0
 * Fix for #46 sourcing gprof2dot when the local venv has not been activated

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

