import os
import traceback
import logging
import socket

import pytest
import py.builtin
from pytest_fixture_config import Config

log = logging.getLogger(__name__)


class FixtureConfig(Config):
    __slots__ = ('host', 'port', 'uri', 'browser')

CONFIG = FixtureConfig(
    host=os.getenv('SELENIUM_HOST', socket.gethostname()),
    port=os.getenv('SELENIUM_PORT', '4444'),
    uri=os.getenv('SELENIUM_URI'),
    browser=os.getenv('SELENIUM_BROWSER', 'chrome'),
)


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
            "Unknown browser requested '{0}'.".format(browser)
        )
    return b


@pytest.yield_fixture(scope='function')
def webdriver(request):
    """ Connects to a remote selenium webdriver and returns the browser handle.
        Scoped on a per-function level so you get one browser window per test.
        Creates screenshots automatically on test failures.
        
        Attributes
        ----------
        root_uri:  URI to the pyramid_server fixture if it's detected in the test run
    """
    from selenium import webdriver

    selenium_uri = CONFIG.uri
    if not selenium_uri:
        selenium_uri = 'http://{0}:{1}'.format(CONFIG.host, CONFIG.port)

    # Look for the pyramid server funcarg in the current session, and save away its root uri
    root_uri = []
    try:
        root_uri.append(request.getfuncargvalue('pyramid_server').uri)
    except LookupError:
        pass

    driver = webdriver.Remote(
        selenium_uri,
        browser_to_use(webdriver, CONFIG.browser)
    )

    if root_uri:
        driver.__dict__['root_uri'] = root_uri[0]

    yield driver

    driver.close()


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item, call):
    """ Screenshot failing tests
    """
    if not hasattr(item, 'funcargs') or not 'webdriver' in item.funcargs:
        return
    if not call.excinfo or call.excinfo.errisinstance(pytest.skip.Exception):
        return
    fname = item.nodeid.replace('/', '__') + '.png'
    py.builtin.print_("Saving screenshot to %s" % fname)
    try:
        item.funcargs['webdriver'].get_screenshot_as_file(fname)
    except:
        print(traceback.format_exc())
