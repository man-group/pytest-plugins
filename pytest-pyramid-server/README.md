# Py.test Pyramid Server Fixture

Pyramid server fixture for py.test. The server is session-scoped by default 
and run in a subprocess and temp dir, and as such is a 'real' server that you 
can point a Selenium webdriver at. 
                      
## Installation

Install using your favourite package manager:

```bash
    pip install pytest-pyramid
    #  or..
    easy_install pytest-pyramid
```

Enable the fixture explicitly in your tests or conftest.py (not required when using setuptools entry points):

```python
    pytest_plugins = ['pytest_pyramid_server']
```
                      
## Configuration

This fixture searches for its configuration in the current working directory
called 'testing.ini'. All .ini files in the cwd will be copied to the tempdir
so that paster-style config chaining still works. For example:

    my-pyramid-app/
                  src/             # Project code is in here
                  setup.py         # Project setup.py
                  development.ini  # Development settings
                  production.ini   # Production settings
                  testing.ini      # Testing settings, will be used if tests 
                                   # are invoked using 'py.test' from this 
                                   # directory

## Example 

Here's a noddy test case showing the main functionality:

```python
    def test_pyramid_server(pyramid_server):
        # This is the http://{host}:{port} of the running server. It will attempt to resolve
        # to externally accessable IPs so a web browser can access it.
        assert pyramid_server.uri.startswith('http')
        
        # GET a document from the server.
        assert pyramid_server.get('/orders/macbooks', as_json=True)  == {'id-1234': 'MPB-15inch'}
        
        # POST a document to the server.
        assert pyramid_server.post('/login', 'guest:password123').response_code == 200
        
        # ``path.py`` path object to the running config file
        assert pyramid_server.working_config.endswith('testing.ini')
```        
        
## `PyramidServer` class

Using this with the default `pyramid_server` py.test fixture is good enough for a lot of 
use-cases however you may wish to have more fine-grained control about the server configuration.
To do this you can use the underlying server class directly - this is an implenentation of the
`pytest-server-fixture` framework and as such acts as a context manager:

```python
    from pytest_pyramid import PyramidTestServer
    
    def test_custom_server():
        with PyramidTestServer(
               # You can specify you own config directory and name
               config_dir='/my/config',
               config_fileme='my_testing.ini',
                               
              # You can set arbitrary config variables in the constructor
              extra_config_vars={'my_config_section': {'my_dbname: 'foo',
                                                       'my_dbpass: 'bar'}}
           ) as server:
               assert not server.dead
               assert 'my_dbname = foo' in server.working_config.text()
               
        # Server should now be dead
        assert server.dead   
```
        
## `pytest-webdriver` and [PageObjects](https://page-objects.readthedocs.org/en/latest/) integration

The `pytest-webdriver` plugin will detect when this plugin is active and set its default base
URL to the url of the running server. This is a nice way of avoiding lots of string manipulation
in your browser tests when using Page Objects:

```python
    from page_objects import PageObject, PageElement
    
    class LoginPage(PageObject):
        username = PageElement(id_='username')
        password = PageElement(name='password')
        login = PageElement(css='input[type="submit"]')

    def test_login_page(webdriver, pyramid_server):
        page = LoginPage(webdriver)
        page.login.click()
        page.get('/foo/bar')
        assert webdriver.getCurrentUrl() == pyramid_server.uri + '/foo/bar'
```        
