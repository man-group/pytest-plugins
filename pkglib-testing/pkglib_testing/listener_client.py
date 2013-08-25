import socket
import json

def client(host='localhost', port=8101):
    s = socket.socket()
    s.connect((host, port))
    s.send(json.dumps('a message from client'))
    print s.recv(1024)
    s.close()

if __name__ == '__main__':
    client(port=8102)
