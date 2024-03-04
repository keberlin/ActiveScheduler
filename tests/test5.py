import logging
import os
from threading import Thread
from typing import Callable

from activescheduler import ActiveObject, scheduler

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CHUNK_SIZE = 100


class FileReaderChunked(ActiveObject):
    def __init__(self, fname: str, callback: Callable):
        super().__init__()
        self.callback = callback

        # Initialise
        self.file = open(fname, "r")

        # Start
        self.read()

    def process(self):
        # Read the next chunk
        self.data = self.file.read(CHUNK_SIZE)
        self.complete()

    def read(self):
        self.set_active()
        self.thread = Thread(target=self.process)
        self.thread.start()

    def run(self):
        # Notify the consumer about the next chunk of data, empty indicates it's finished
        self.callback(self.data)
        if not self.data:
            # Finish
            self.file.close()
            return

        self.read()


class FileReaderContinuous(ActiveObject):
    def __init__(self, fname: str, callback: Callable):
        super().__init__()
        self.callback = callback

        # Initialise
        self.file = open(fname, "r")

        # Start
        self.set_active()
        self.thread = Thread(target=self.process)
        self.thread.start()

    def process(self):
        while True:
            # Read the next chunk
            self.data = self.file.read(CHUNK_SIZE)
            self.complete()
            if not self.data:
                break
            # self.wait_for_active()

    def run(self):
        # Notify the consumer about the next chunk of data, empty indicates it's finished
        self.callback(self.data)
        if not self.data:
            # Finish
            self.file.close()
            return

        self.set_active()


FNAME = "data.txt"

path = os.path.dirname(__file__)
fname = os.path.join(path, FNAME)

with open(fname, "r") as f:
    file_contents = f.read()


class FileConsumer:
    def __init__(self, cls, fname: str, callback: Callable):
        self.cls = cls
        self.fname = fname
        self.callback = callback
        self.contents = ""

    def notify_data(self, data: str):
        self.contents += data
        if not data:
            # Finish
            self.callback(self.contents)

    def start(self):
        # Start
        self.reader = self.cls(self.fname, self.notify_data)


def notify_contents(contents: str):
    assert contents == file_contents


# Non-blocking
consumer = FileConsumer(FileReaderChunked, fname, notify_contents)
consumer.start()

# Non-blocking
consumer = FileConsumer(FileReaderContinuous, fname, notify_contents)
consumer.start()


scheduler.start()
