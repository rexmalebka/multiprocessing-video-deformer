import cv2
import numpy as np

import argparse
import os
import sys

from multiprocessing import current_process, Manager, Process
from multiprocessing.connection import Listener
from time import sleep
from client import Source, Frame
import queue

manager = Manager()

def viewer(q, name):
    print(f'\t\tstarting frame viewer, waiting for instructions')
    frame = q.get()
    cv2.namedWindow(name, cv2.WINDOW_NORMAL)

    while True:
        try:
            cv2.imshow(name, frame)
            cv2.waitKey(1)
            frame = q.get()
            
        except KeyboardInterrupt:
            cv2. destroyWindow(name) 

class putter:
    def __init__(self, server_queue, name, path):
        self.server_queue = server_queue

        queue_viewer = manager.Queue(1)
        self.queue_viewer = queue_viewer

        self.name = name
        
        print(f'\tstarting frames processor')
        
        viewer_proc = Process(target = viewer, args=(queue_viewer, name), name=f'viewer-{name}')
        viewer_proc.start()

        self.instructions = []

        self.path = path
        self.cap =  cv2.VideoCapture(self.path)

        self.buffer = []
        self.buffer_size = 20 

        self.error = None
        self.resolution = None

        self.instructions = self.server_queue.get()
        while True:
            print(self.instructions)
            if type(self.instructions) == list and len(self.instructions) > 0:
                instruction = self.instructions[0]
                self.instructions = self.instructions[1:] + [instruction]

                frame = self.execute(instruction)
                self.queue_viewer.put(frame)
            elif self.instructions == 'sleep':
                timeout = self.server_queue.get()
                self.queue_viewer.put(timeout)
                
                print(f'\tsleep time changed to {timeout}')
                self.load(path)
                self.instructions = []
            elif self.instructions == 'load':
                path = self.server_queue.get()
                print(f'\tLoading video {path}')
                self.load(path)
                self.instructions = []

            elif self.instructions == 'resolution':
                res = self.server_queue.get()
                self.resolution = res

                self.instructions = []
                print(f'\tchanging resolution to {res}')

            elif self.instructions == 'buffer':
                buffer_size = self.server_queue.get()
                self.buffer_size = buffer_size
                
                while len(self.buffer) > buffer_size:
                    self.buffer.pop(0)

                self.instructions == []
                print(f'\tchanging buffer size to {buffer_size}')
            else:
                frame = self.read_frame()
                self.queue_viewer.put(frame)
                
            try:
                instructions = self.server_queue.get_nowait()
                self.instructions = instructions
                print("\tinstructions were updated")
            except queue.Empty:
                pass

    def load(self, path):
        print(f"\tLoading {path}")
        self.path = path
        self.cap =  cv2.VideoCapture(self.path)


    def read_frame(self):
        res, frame = self.cap.read()

        if not res:
            self.cap  = cv2.VideoCapture(self.path)
            res, frame = self.cap.read()

        if self.resolution != None:
            frame = cv2.resize(frame, self.resolution)


        self.buffer.append(frame)

        if len(self.buffer) > self.buffer_size:
            self.buffer.pop(0)

        return frame

    def run_task(self, task, frame, buffer):
        try:
            func = eval(task[0]) if type(task[0]) == str else task[0]
            args = [] 
            kwargs = {}

            for a in task[1]:
                if type(a) == str:
                    args.append(eval(a))
                else:
                    args.append(a)

            for a in task[2]:
                if task[2][a] == str:
                    kwargs[a] = eval( task[2][a] )
                else: 
                    kwargs[a] = task[2][a]
            
            if 'roi' in kwargs:
                roi = kwargs['roi']
                del kwargs['roi']

                nframe = func(*args, **kwargs)

                frame[
                        roi[0][0] : roi[0][1],
                        roi[1][0] : roi[1][1],
                        ] = nframe[
                                roi[0][0] : roi[0][1],
                                roi[1][0] : roi[1][1],
                                ]
                return frame

            frame = func(*args, **kwargs)
            return frame

        except Exception as e:
            self.log(e)
            return frame
        return frame

    def log(self, e):
        if str(e) != str(self.error):
            print(f"\t(Error) {e}")
        self.error = e

    def execute(self, instruction):
        frame = self.read_frame()
        buffer = self.buffer

        if hasattr(instruction,'__call__'):
            return instruction(frame)
        elif type(instruction) == tuple:
            return self.run_task(instruction, frame, buffer)
        elif type(instruction) == list:
            for subtask in instruction:
                frame = self.run_task(subtask, frame,buffer)
        return frame
    

# play, seek n, sleep 1, loop,
class Server:
    def __init__(self):
        self.videos = {}

        self.commands = {
                "load": self.load,
                'filter': self.filter,
                "resolution":self.resolution,
                'buffer': self.buffer,
                'sleep': self.sleep,
                "seek": 6
                }

    def sleep(self, data, conn):
        sid, timeout = data

        if sid in self.videos:
            self.videos[sid].put('sleep')
            self.videos[sid].put( timeout )

    def filter(self, data, conn):
        sid = data[0]
        filters = data[1]

        if sid in self.videos:
            self.videos[sid].put(filters)

    def buffer(self, data):
        sid, buffer_size = data

        if sid in self.videos:
            self.videos[sid].put('buffer')
            self.videos[sid].put( buffer_size )

    def resolution(self, data, conn):
        sid, width, height = data

        if sid in self.videos:
            self.videos[sid].put('resolution')
            self.videos[sid].put( (width, height) )
        

    def load(self, data, conn):
        sid = data[0]
        path = data[1]

        if not sid in self.videos:
            print(f'loading source {sid} "{path}"')
            
            manager = Manager()
            self.videos[sid] = manager.Queue()
            p = Process(target=putter, args=( self.videos[sid], sid, path ), name=f"putter-{sid}")
            p.start()
        else:
            self.videos[sid].put('load' )
            self.videos[sid].put( path )

    def handle(self,msg, conn):
        if type(msg) == tuple and msg[0] in self.commands:
            self.commands[msg[0]](msg[1:], conn)

    def start(self):
        print(f"starting server on localhost:12345 on pid: {current_process().pid}")
        self.running = True

        with Listener(('localhost', 12345) ) as listener:
            while self.running:
                with listener.accept() as conn:
                    while True:
                        try:
                            msg = conn.recv()
                            if msg == 'CLOSE':
                                self.running = False
                                break
                            else:
                                self.handle(msg, conn)
                                break
                            print(conn)
                        except EOFError:
                            break
                        except KeyboardInterrupt:
                            self.running = False
                            break

if __name__ == '__main__':
    server = Server()
    server.start()

