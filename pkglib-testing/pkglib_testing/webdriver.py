import subprocess
import os

from selenium.webdriver import Remote, DesiredCapabilities
from splinter.driver.webdriver import BaseWebDriver
from splinter.cookie_manager import CookieManagerAPI
from splinter.driver.webdriver.remote import WebDriverElement



# TODO: marry this up with pytest.webdriver

class RemoteWebDriver(BaseWebDriver):

    driver_name = "Remote Chrome webdriver"

    def __init__(self, server='localhost', port=4444, root_uri=None):
        self.old_popen = subprocess.Popen

        self._patch_subprocess()

        self.driver = Remote('http://%s:%s/wd/hub' % (server, port),
                             DesiredCapabilities().FIREFOX) if os.getenv("SELENIUM_USE_FIREFOX") \
            else Remote('http://%s:%s' % (server, port), DesiredCapabilities().CHROME)

        self._unpatch_subprocess()

        self.element_class = WebDriverElement

        self._cookie_manager = CookieManagerAPI()

        super(RemoteWebDriver, self).__init__()

        if root_uri:
            self.driver.__dict__['root_uri'] = root_uri
