# pytest-listener

Simple JSON listener using TCP that listens for data and stores it in a queue for later retrieval.
                            
## Installation
                      
Install using your favourite package manager:

```bash
    pip install pytest-listener
    #  or..
    easy_install pytest-listener
```

Enable the fixture explicitly in your tests or conftest.py (not required when using setuptools entry points):

```python
    pytest_plugins = ['pytest_listener']
```
                      
## Basic Test Usage

Here's a test showing the basic functionality:

```python
    def test_listener(listener):
        data1 = {'foo': 1}
        listener.send(some_data)
        
        data2 = {'bar': 2}
        listener.send(some_data)
        
        assert listener.receive() == data1
        assert listener.receive() == data2
        
        data3 = {'baz': 3}
        listener.send(some_data)
        
        # Clear the listening queue - this deletes data3
        listener.clear_queue()
        
        data2 = {'qux': 4}
        listener.send(some_data)
        assert listener.recieve() == data3
```