import os

import pytest
import py.builtin

from pkglib import CONFIG


def browser_to_use(webdriver, browser):
    """Recover the browser to use with the given webdriver instance.

    The browser string is case insensitive and needs to be one of the values
    from BROWSERS_CFG.

    """
    browser = browser.strip().upper()

    # Have a look the following to see list of supported browsers:
    #
    #   http://selenium.googlecode.com/git/docs/api/
    #     py/_modules/selenium/webdriver/common/desired_capabilities.html
    #
    b = getattr(webdriver.DesiredCapabilities(), browser, None)
    if not b:
        raise ValueError(
            "Unknown browser requested '{}'.".format(browser)
        )

    #print "{}\n\nbrowser: {}\n\n{}".format('-'*80, browser, '-'*80)

    return b


def pytest_funcarg__webdriver(request):
    """ Connects to a remote selenium webdriver and returns the browser handle.
        Scoped on a per-function level so you get one browser window per test.

        To use this function, follow the following steps:
        1) Nominate a Windows host. This can be your desktop machine, or a VM
        2) Download the latest zip file from here: https://code.google.com/p/chromedriver/downloads/list
        3) Unpack onto the target host, and run the unpacked chromedriver.exe file
        4) Set the environment variables SELENIUM_HOST and SELENIUM_PORT to be the windows host, the default
           port number is 9515
        5) Include this funcarg in your test like so::

               from pkglib.testing.pytest.selenium import pytest_funcarg__webdriver

               def test_mywebpage(webdriver):
                   webdriver.get('http://www.google.com')

        *Important* If there is a pyramid_server funcarg also running in the current test, it will
         set the 'root_uri' attribute on the webdriver instance so you can use this to base
         URLs off of.
    """
    from selenium import webdriver
    try:
        os.environ['SELENIUM_HOST']
        os.environ['SELENIUM_PORT']
    except KeyError:
        print "Please ensure SELENIUM_HOST and SELENIUM_PORT are set in the environment"
        raise

    # Look for the pyramid server funcarg in the current session, and save away its root uri
    root_uri = []
    try:
        root_uri.append(request.getfuncargvalue('pyramid_server').uri)
    except LookupError:
        pass

    def setup():
        browser = os.environ.get('SELENIUM_BROWSER', 'chrome')
        res = webdriver.Remote(
            'http://%s:%s' % (
                os.environ["SELENIUM_HOST"],
                os.environ['SELENIUM_PORT']
            ),
            browser_to_use(webdriver, browser)
        )
        if root_uri:
            res.__dict__['root_uri'] = root_uri[0]
        return res

    def teardown(driver):
        driver.close()

    return request.cached_setup(
        setup=setup,
        teardown=teardown,
        scope='function',
    )


# Can't use this, it's run too late.
#def pytest_addoption(parser):
#    parser.addoption("--screenshot", action="store_true", default=False,
#        help="Save a screenshot for each failing Selenium test.")


@pytest.mark.tryfirst
def pytest_runtest_makereport(item, call, __multicall__):
    if not 'webdriver' in item.funcargs:
        return
    #if not item.config.getvalue('screenshot'):
    #    return
    if not call.excinfo or call.excinfo.errisinstance(pytest.skip.Exception):
        return
    fname = item.nodeid.replace('/', '__') + '.png'
    py.builtin.print_("Saving screenshot to %s" % fname)
    item.funcargs['webdriver'].get_screenshot_as_file(fname)
    return
