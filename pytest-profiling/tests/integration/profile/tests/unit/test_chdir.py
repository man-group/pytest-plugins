import os

def test_chdir():
    os.mkdir('foo')
    os.chdir('foo')
