from multiprocessing.connection import Client
import os
import cv2
import numpy as np

class Frame:
    pass

def send( addr='localhost', port=12345,msg=None, callback=None):
    conn = Client((addr, port))

    conn.send(msg)

    if callback != None:
        value = callback(conn.recv())
        conn.close()
        return value
    else:
        conn.close()



class Source:
    def __init__(self, name):
        self.path = ''
        self.name = name
        self.actions = []

    def clear(self):
        self.actions = []
        self.send()

    def do(self, func, *args, **kwargs):
        self.actions.append(
                (
                    func,
                    args,
                    kwargs
                    )
                )
        return self

    def __enter__(self):
        self.compose = True
        self.actions_ = self.actions
        self.actions = []
        return self

    def __exit__(self, *args):
        print("args", args)
        bunch = self.actions
        self.actions = self.actions_
        del self.actions_ 

        self.actions.append( bunch)
        

    def load(self, path=''):
        if os.path.exists(path):
            print(f'loading "{path}"')
            self.path = path
            send(msg=('load', self.name, path))
        return self

    def buffer(self, buf):
        send(msg=('buffer', self.name, buf))

    def resolution(self, width, height):
        send(msg=('resolution', self.name, width, height))

    def send(self):
        send(msg=('filter', self.name, self.actions))


    def __getitem__(self, item):
        s = Source(self.name)
        s.actions = [*self.actions, item]
        return s

    def __add__(self, other):
        if type(other) == Source:
            self.actions.extend(other.actions)
        return self 
    def __rshift__(self, other):
        print("seeking 4 frames")
        print(other)


if __name__ == '__main__':

    s0 = Source('s0')
