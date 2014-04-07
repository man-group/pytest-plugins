'''
Created on 1 Oct 2012

@author: bfitzgerald
'''
from .page_objects import PageObject, page_element


class JasmineResultsPage(PageObject):
    failing_alert_bar = page_element(css='.failingAlert.bar')

    def __init__(self, webdriver, suite_url='js-test'):
        super(JasmineResultsPage, self).__init__(webdriver)
        self.w.get('%s/%s' % (self.w.root_uri, suite_url))
        assert 'JS Tests' in self.w.title

    def get_number_of_failing_tests(self):
        if self.failing_alert_bar:
            msg = self.failing_alert_bar.text
            return int(msg.split()[1])
        else:
            return 0
