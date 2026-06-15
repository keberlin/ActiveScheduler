import logging
import os

from activescheduler import ActiveObject, scheduler

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

CHUNK_SIZE = 100


class FileReaderNonBlocking(ActiveObject):
    def __init__(self, fname: str):
        super().__init__()

        # Initialise
        self.file = open(fname, "r")
        self.contents = ""

        # Start
        self.read()

    def read(self):
        # Read in a new chunk
        data = self.file.read(CHUNK_SIZE)
        if not data:
            self.file.close()
            self.cancel()
            return
        self.complete(data)

    def run(self, data: str):
        self.contents += data

        # Next chunk
        self.read()


FNAME = "data.txt"

path = os.path.dirname(__file__)
fname = os.path.join(path, FNAME)


# Non-blocking
reader = FileReaderNonBlocking(fname)


scheduler.start()

# Check that the reader has read the entire contents of fname
with open(fname, "r") as f:
    assert reader.contents == f.read()
