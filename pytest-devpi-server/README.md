# Py.test DevPi Server Fixture

DevPi server fixture for ``py.test``. The server is session-scoped by default 
and run in a subprocess and temp dir to cleanup when it's done. 

After the server has started up it will create a single user with a password, 
and an index for that user. It then activates that index and provides a
handle to the ``devpi-client`` API so you can manipulate the server in your tests.
                      
## Installation

Install using your favourite package manager:

```bash
    pip install pytest-devpi-server
    #  or..
    easy_install pytest-devpi-server
```

Enable the fixture explicitly in your tests or conftest.py (not required when using setuptools entry points):

```python
    pytest_plugins = ['pytest_devpi_server']
```
                      
## Example 

Here's a noddy test case showing the main functionality:

```python
    def test_devpi_server(devpi_server):
        # This is the client API for the server that's bound directly to the 'devpi' command-line tool.
        # Here we list the available indexes
        print(devpi_server.api('use', '-l'))
        
        # Create and use another index
        devpi_server.api('index', '-c', 'myindex')
        devpi_server.api('index', 'use', 'myindex')

        # Upload a package 
        import os
        os.chdir('/path/to/my/setup/dot/py')
        devpi_server.api('upload')

        # Get some json data
        import json
        res = devpi_server.api('getjson', '/user/myindex')
        assert json.loads(res)['result']['projects'] == ['my-package-name']

```        
        
## `DevpiServer` class

Using this with the default `devpi_server` py.test fixture is good enough for a lot of 
use-cases however you may wish to have more fine-grained control about the server configuration.

To do this you can use the underlying server class directly - this is an implenentation of the
`pytest-server-fixture` framework and as such acts as a context manager:

```python
    import json
    from pytest_devpi_server import DevpiServer
    
    def test_custom_server():
        with DevPiServer(
              # You can specify you own initial user and index
              user='bob',
              password='secret',
              index='myindex',

              # You can provide a zip file that contains the initial server database, 
              # this is useful to pre-load any required packages for a test run
              data='/path/to/data.zip'
           ) as server:

               assert not server.dead
               res = server.api('getjson', '/bob/myindex')
               assert 'pre-loaded-package' in json.loads(res)['result']['projects'] 
               
        # Server should now be dead
        assert server.dead   
```
