import sys
import six.moves


def move_attr(*args):
    move = six.MovedAttribute(*args)
    six.add_move(move)

move_attr('BaseHandler', 'urllib2', 'urllib.request')
move_attr('HTTPBasicAuthHandler', 'urllib2', 'urllib.request')
move_attr('HTTPPasswordMgr', 'urllib2', 'urllib.request')
move_attr('HTTPPasswordMgrWithDefaultRealm', 'urllib2', 'urllib.request')
move_attr('Request', 'urllib2', 'urllib.request')
move_attr('build_opener', 'urllib2', 'urllib.request')
move_attr('addinfourl', 'urllib2', 'urllib.request')
move_attr('install_opener', 'urllib2', 'urllib.request')
move_attr('urlopen', 'urllib2', 'urllib.request')

move_attr('HTTPError', 'urllib2', 'urllib.error')
move_attr('URLError', 'urllib2', 'urllib.error')

move_attr('quote', 'urllib2', 'urllib.parse')
move_attr('urlparse', 'urlparse', 'urllib.parse')
move_attr('urljoin', 'urlparse', 'urllib.parse')
move_attr('urlencode', 'urllib', 'urllib.parse')
move_attr('ServerProxy', 'xmlrpclib', 'xmlrpc.client')

move_attr('ExitStack', 'contextlib2', 'contextlib')

sys.modules[__name__] = six.moves
