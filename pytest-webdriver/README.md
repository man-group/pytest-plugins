# Pytest Webdriver Fixture

This fixture provides a configured webdriver for Selenium browser tests, that takes screenshots for you
on test failures.


## Installation

Install using your favourite package installer:
```bash
    pip install pytest-webdriver
    # or
    easy_install pytest-webdriver
```
    
Enable the fixture explicitly in your tests or conftest.py (not required when using setuptools entry points):

```python
    pytest_plugins = ['pytest_webdriver']
```

## Quickstart 

This fixture connects to a remote selenium webdriver and returns the browser handle.
It is scoped on a per-function level so you get one browser window per test.

To use this fixture, follow the following steps.

1. Nominate a browser host, and start up the webdriver executable on that host. 
2. Download the latest zip file from here: https://sites.google.com/a/chromium.org/chromedriver/downloads
3. Unpack onto the target host, and run the unpacked chromedriver binary executable. 
4. Set the environment variable ``SELENIUM_HOST`` to the IP address or hostname of the browser host. This defaults to the local hostname. 
5. Set the environment variable ``SELENIUM_PORT`` to the port number of the webdriver server. The default port number is 4444. 
6. Set the environment variable ``SELENIUM_BROWSER`` to the browser type. Defaults to ``chrome``. 
7. Use the fixture as a test argument:

```python
       def test_mywebpage(webdriver):
           webdriver.get('http://www.google.com')
``` 
           
## `SELENIUM_URI` setting

You can also specify the selenium server address using a URI format using the SELENIUM_URL environment variable::

```bash
    $ export SELENIUM_URI=http://localhost:4444/wd/hub
```

This is needed when dealing with selenium server and not chrome driver (see https://groups.google.com/forum/?fromgroups#!topic/selenium-users/xodZDJxt81o). 
If SELENIUM_URI is not defined SELENIUM_HOST & SELENIUM_PORT will be used.


## Automatic screenshots

When one of your browser tests fail, this plugin will take a screenshot for you and save it in the current
working directory. The name will match the logical path to the test function that failed, like:

    test_login_page__LoginPageTest__test_unicode.png

        
## `pytest-webdriver` and [PageObjects](https://page-objects.readthedocs.org/en/latest/)


If there is a pyramid_server fixture from the also running in the current test, it will detect this and set the ``root_uri`` attribute on the webdriver instance:

```python  
    def test_my_pyramid_app(webdriver, pyramid_server):
        assert webdriver.root_uri == pyramid_server.uri
```  
        
Why is this needed, you may ask? It can be used by the `PageObjects` library to automatically set the base URL to your web app. This saves on a lot of string concatenation. For example:

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