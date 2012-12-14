'''
Created on 1 Oct 2012

@author: eeaston
'''
import inspect

import pytest
import mock
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver


from pkglib.testing.page_objects import (PageObject, PageElement, MultiPageElement, page_element,
                                      multi_page_element)


def test_page_element():
    elem = page_element(css='foo')
    assert elem.locator == (By.CSS_SELECTOR, 'foo')
    assert inspect.isclass(PageElement)


def test_multi_page_element():
    elem = multi_page_element(id_='bar')
    assert elem.locator == (By.ID, 'bar')
    assert inspect.isclass(MultiPageElement)


def test_page_element_bad_args():
    with pytest.raises(ValueError):
        page_element()
    with pytest.raises(ValueError):
        page_element(id_='foo', xpath='bar')


def test_get_descriptors():
    class TestPage(PageObject):
        test_elem1 = page_element(css='foo')
        test_elem2 = page_element(css='bar')

    webdriver = mock.Mock(spec=WebDriver)
    webdriver.find_element.side_effect = ["XXX", "YYY"]
    page = TestPage(webdriver=webdriver)
    assert page.test_elem1 == "XXX"
    assert page.test_elem2 == "YYY"


def test_set_descriptors():
    class TestPage(PageObject):
        test_elem1 = page_element(css='foo')
        test_elem2 = page_element(css='bar')

    webdriver = mock.Mock(spec=WebDriver)
    page = TestPage(webdriver=webdriver)
    elem = mock.Mock(name="My Elem")
    webdriver.find_element.return_value = elem
    page.test_elem1 = "XXX"
    elem.send_keys.assert_called_once_with('XXX')
