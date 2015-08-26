import time

import pytest

from . import server


@pytest.fixture(scope='module')
def listener(request):
    """ Simple module-scoped network listener. 
    
    Methods
    -------
    send(data, timeout):  Send data to the listener
    recieve(timeout):     Recieve data from the listener
    clear_queue():        Clear the listener queue
    """
    res = server.Listener()
    res.start()
    # Wait for socket to become available
    time.sleep(1)
    request.addfinalizer(lambda p=res: server.stop_listener(p))
    return res
