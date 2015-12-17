# Pytest Server Fixtures

This library provides an extensible framework for running up real network
servers in your tests, as well as a suite of fixtures for some well-known webservices 
and databases.
                      
## Batteries Included

| Fixture | Extra Dependency Name
| ------- | ---------------------
| MongoDB                                | mongodb 
| Redis                                  | redis
| RethinkDB                              | rethinkdb
| Apache Httpd                           | 
| Jenkins                                | jenkins
| Xvfb (X-Windows Virtual Frame Buffer)  |

## Installation

Installation of this package varies on which parts of it you would like to use. 
It uses optional dependencies (specified in the table above) to reduce the number 
of 3rd party packages required. This way if you don't use MongoDB, you don't need 
to install PyMongo. 

```bash
    # Install with support for just mongodb
    pip install pytest-server-fixtures[mongodb]
    
    # Install with support for mongodb and jenkins
    pip install pytest-server-fixtures[mongodb,jenkins]
    
    # Install with only core library and support for httpd and xvfp
    pip install pytest-server-fixtures
```               

Enable the fixture explicitly in your tests or conftest.py (not required when using setuptools entry points):

```python
    pytest_plugins = ['pytest_server_fixtures.httpd',
                      'pytest_server_fixtures.jenkins',
                      'pytest_server_fixtures.mongo',
                      'pytest_server_fixtures.redis',
                      'pytest_server_fixtures.rethink',
                      'pytest_server_fixtures.xvfb',
                      ]
```

## Configuration

The fixtures are configured using the following evironment variables:

| Setting | Description | Default
| ------- | ----------- | -------
| SERVER_FIXTURES_HOSTNAME      | Hostname that servers will listen on | Current default hostname
| SERVER_FIXTURES_MONGO_BIN     | Directory containing the `mongodb` executable | `/usr/bin`
| SERVER_FIXTURES_REDIS         | Redis server executable | `/usr/sbin/redis-server`
| SERVER_FIXTURES_RETHINK       | RethinkDB server executable |  `/usr/bin/rethinkdb`
| SERVER_FIXTURES_HTTPD         | Httpd server executable | `/usr/sbin/apache2`
| SERVER_FIXTURES_HTTPD_MODULES | Httpd modules directory | `/usr/lib/apache2/modules`
| SERVER_FIXTURES_JAVA          | Java executable used for running Jenkins server | `java`
| SERVER_FIXTURES_JENKINS_WAR   | `.war` file used to run Jenkins | `/usr/share/jenkins/jenkins.war`
| SERVER_FIXTURES_XVFB          | Xvfb server executable | `/usr/bin/Xvfb`

## Common fixture properties

All of these fixtures follow the pattern of spinning up a server on a unique port and 
then killing the server and cleaning up on fixture teardown.

All test fixtures share the following properties at runtime:

| Property | Description 
| -------- | ----------- 
| hostname  | Hostname that server is listening on
| port      | Port number that the server is listening on
| dead      | True/False: am I dead yet?
| workspace | `path.py` object for the temporary directory the server is running out of

## MongoDB

The `mongo` module contains the following fixtures:

| Fixture Name | Description 
| ------------ | ----------- 
| mongo_server      | Function-scoped MongoDB server
| mongo_server_sess | Session-scoped MongoDB server
| mongo_server_cls  | Class-scoped MongoDB server

All these fixtures have the following properties: 

| Property | Description 
| -------- | ----------- 
| api | `pymongo.MongoClient` connected to running server

Here's an example on how to run up one of these servers:

```python
def test_mongo(mongo_server):
    db = mongo_server.api.mydb
    collection = db.test_coll
    test_coll.insert({'foo': 'bar'})
    assert test_coll.find_one()['foo'] == 'bar'
```

## Redis

The `redis` module contains the following fixtures:

| Fixture Name | Description 
| ------------ | ----------- 
| redis_server      | Function-scoped Redis server
| redis_server_sess | Session-scoped Redis server

All these fixtures have the following properties: 

| Property | Description 
| -------- | ----------- 
| api | `redis.Redis` client connected to the running server

Here's an example on how to run up one of these servers:

```python
def test_redis(redis_server):
    redis_server.api.set('foo': 'bar')
    assert redis_server.api.get('foo') == 'bar'
```

## RethinkDB

The `rethink` module contains the following fixtures:

| Fixture Name | Description 
| ------------ | ----------- 
| rethink_server       | Function-scoped Redis server
| rethink_server_sess | Session-scoped Redis server
| rethink_unique_db | Session-scoped unique db
| rethink_module_db | Module-scoped unique db
| rethink_make_tables | Module-scoped fixture to create named tables
| rethink_empty_db | Function-scoped fixture to empty tables created in `rethink_make_tables`

The server fixtures have the following properties

| Property | Description 
| -------- | ----------- 
| conn | `rethinkdb.Connection` to the `test` database on the running server


Here's an example on how to run up one of these servers:

```python
def test_rethink(rethink_server):
    conn = rethink_server.conn
    conn.table_create('my_table').run(conn)
    inserted = conn.table('my_table').insert({'foo': 'bar'}).run(conn)
    assert conn.get(inserted.generated_keys[0])['foo'] == 'bar
```

### Creating Tables

You can create tables for every test in your module like so:

```python
FIXTURE_TABLES = ['accounts','transactions']

def test_table_creation(rethink_module_db, rethink_make_tables):
    conn = rethink_module_db
    assert conn.table_list().run(conn) == ['accounts', 'transactions']
```

### Emptying Databases

RehinkDb is annecdotally slower to create tables that it is to empty them 
(at least at time of writing), so we have a fixture that will empty out
tables between tests for us that were created with the `rethink_make_tables`
fixture above:


```python
FIXTURE_TABLES = ['accounts','transactions']

def test_put_things_in_db(rethink_module_db, rethink_make_tables):
    conn = rethink_module_db
    conn.table('accounts').insert({'foo': 'bar'}).run(conn)
    conn.table('transactions').insert({'baz': 'qux'}).run(conn)


def test_empty_db(rethink_empty_db):
    conn = rethink_empty_db
    assert not conn.table('accounts').run(conn)
    assert not conn.table('transactions').run(conn)
```

# Apache `httpd` Fixture

The `httpd` module contains the following fixtures:

| Fixture Name | Description 
| ------------ | ----------- 
| httpd_server | Function-scoped httpd server to use as a web proxy 

The fixture has the following properties at runtime:

| Property | Description 
| -------- | ----------- 
| document_root | `path.path` to the document root 
| log_dir | `path.path` to the log directory

Here's an example showing some of the features of the fixture:

```python
def test_httpd(httpd_server):
    # Log files can be accessed by the log_dir property
    assert 'access.log' in [i.basename() for i in httpd_server.log_dir.files()]
    
    # Files in the document_root are accessable by HTTP
    hello = httpd_server.document_root / 'hello.txt'
    hello.write_text('Hello World!')
    response = httpd_server.query_url('/hello.txt')
    assert response.status_code == 200
    assert response.text == 'Hello World!'
```

## Proxy Rules

An httpd server on its own isn't super-useful, so the underlying class for the
fixture has options for configuring it as a reverse proxy. Here's an example
where we've pulled in a `pytest-pyramid` fixture and set it up to be proxied
from the `httpd` server::

```python
import pytest
from pytest_server_fixtures.httpd import HTTPDServer

pytest_plugins=['pytest_pyramid']

@pytest.yield_fixture()
def proxy_server(pyramid_server):

    # Configure the proxy rules as a dict of source -> dest URLs
    proxy_rules = {'/downstream/' : pyramid_server.url
                  }
                
    server = HTTPDServer(proxy_rules, 
                         # You can also specify any arbitrary text you want to 
                         # put in the config file
                         extra_cfg = 'Alias /tmp /var/tmp\n',
                         )
    server.start()                        
    yield server
    server.teardown()
    
def test_proxy(proxy_server):
    # This request will be proxied to the pyramid server 
    response = proxy_server.get('/downstream/accounts')
    assert response.status_code == 200
```

