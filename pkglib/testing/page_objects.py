'''
Created on 26 Sep 2012

@author: eeaston

Website testing Page Objects
'''
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By


class PageObject(object):
    """ Page Object pattern.

        Parameters
        ----------

        webdriver: `selenium.webdriver.WebDriver`
            Selenium webdriver instance
        root_uri: `str`
            Root URI, set by the pyramid_server funcarg if available

        Examples
        --------
        With page elements::

            from pkglib.testing.page_objects import PageObject, page_element

            class LoginPage(PageObject):
                username = page_element(id_='username')
                password = page_element(name='username')
                login = page_element(css='input[type="submit"]')

            login_page = LoginPage(webdriver, locators)
            login_page.username = 'foo'
            assert login_page.username.text == 'foo'
            login_page.login.click()

    """
    def __init__(self, webdriver, root_uri=''):
        self.w = webdriver
        self.root_uri = root_uri


class PageElement(object):
    """ Page Element pattern.

        Parameters
        ----------
        webdriver: `selenium.webdriver.WebDriver`
            Selenium webdriver instance

        Required Attributes:
        locator:  (`selenium.webriver.common.by.By`, locator text)
          Eg: 'login.username': (By.ID, 'username'),  (By.XPATH, '//password)'

    """
    locator = None

    def __init__(self):
        assert self.locator is not None

    def __get__(self, instance, owner):
        if not instance:
            return None
        try:
            return instance.w.find_element(*self.locator)
        except NoSuchElementException:
            return None

    def __set__(self, instance, value):
        elem = self.__get__(instance, None)
        if not elem:
            raise ValueError("Can't set value, element not found")
        elem.send_keys(value)


class MultiPageElement(PageElement):
    """ Like `_PageElement` but returns multiple results
    """
    def __get__(self, instance, owner):
        try:
            return instance.w.find_elements(*self.locator)
        except NoSuchElementException:
            return []


# Map factory arguments to webdriver locator enums
_LOCATOR_MAP = {'css': By.CSS_SELECTOR,
                'id_': By.ID,
                'name': By.NAME,
                'xpath': By.XPATH,
                'link_text': By.LINK_TEXT,
                'partial_link_text': By.PARTIAL_LINK_TEXT,
                'tag_name': By.TAG_NAME,
                'class_name': By.CLASS_NAME,
                }


def page_element(klass=PageElement, **kwargs):
    """ Factory method for page elements

        Parameters
        ----------
        css:    `str`
            Use this css locator
        id_:    `str`
            Use this element ID locator
        name:    `str`
            Use this element name locator
        xpath:    `str`
            Use this xpath locator
        link_text:    `str`
            Use this link text locator
        partial_link_text:    `str`
            Use this partial link text locator
        tag_name:    `str`
            Use this tag name locator
        class_name:    `str`
            Use this class locator

        Examples
        --------
        Page Elements can be used like this::

            from pkglib.testing.page_objects import PageObject, page_element
            class MyPage(PageObject)
                elem1 = page_element(css='div.myclass')
                elem2 = page_element(id_='foo')

    """
    if not kwargs:
        raise ValueError("Please specify a locator")
    if len(kwargs) > 1:
        raise ValueError("Please specify only one locator")
    k, v = kwargs.items()[0]

    class Element(klass):
        locator = (_LOCATOR_MAP[k], v)

    return Element()


def multi_page_element(**kwargs):
    """ As for `page_element`, but returns a `MutliPageElement`
    """
    return page_element(klass=MultiPageElement, **kwargs)
