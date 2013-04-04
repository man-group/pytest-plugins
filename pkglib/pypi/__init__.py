from pkglib import CONFIG

import xmlrpc
import clue


def PyPi(uri=None, username=None, password=None):
    """
    Factory method to detect PyPI server implementation and provide the
    correct API object.

    """
    if not uri:
        uri = CONFIG.pypi_url
    if xmlrpc.has_pypi_xmlrpc_interface(uri):
        return xmlrpc.XMLRPCPyPIAPI(uri, username, password)
    else:
        return clue.CluePyPIAPI(uri, username, password)
