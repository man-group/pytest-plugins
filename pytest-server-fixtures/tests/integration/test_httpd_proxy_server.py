import psutil

def test_start_and_stop(httpd_server):
    assert httpd_server.check_server_up()
    pid = int((httpd_server.workspace / 'run' / 'httpd.pid').text())
    httpd_server.kill()
    assert not httpd_server.check_server_up()
    still_running = [i for i in psutil.process_iter()
                     if i.pid == pid or i.ppid == pid]
    assert not still_running


def test_logs(httpd_server):
    files = [i.basename() for i in httpd_server.log_dir.files()]
    for log in ('access.log', 'error.log'):
        assert log in files


def test_get_from_document_root(httpd_server):
    hello = httpd_server.document_root / 'hello.txt'
    hello.write_text('Hello World!')
    response = httpd_server.get('hello.txt')
    assert response.status_code == 200
    assert response.text == 'Hello World!'
