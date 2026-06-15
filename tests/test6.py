import logging
import os
from threading import Thread

from activescheduler import ActiveObject, scheduler

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

CHUNK_SIZE = 100


class FileReaderBlocking(ActiveObject):
    def __init__(self, fname: str):
        super().__init__()

        # Initialise
        self.file = open(fname, "r")
        self.contents = ""

    def run(self, data: str):
        """This will always be called within the main-thread."""
        self.contents += data

    def process(self):
        """Read the file contents in chunks."""

        while True:
            # Read the next chunk
            data = self.file.read(CHUNK_SIZE)
            if not data:
                break
            self.complete(data)  # This won't return until self.run() has been called


FNAME = "data.txt"

path = os.path.dirname(__file__)
fname = os.path.join(path, FNAME)

# Setup active objects
reader = FileReaderBlocking(fname)


def run_blocking_task():
    reader.process()

    # Check that the reader has read the entire contents of fname
    with open(fname, "r") as f:
        assert reader.contents == f.read()

    reader.cancel()


# Create a new thread
thread = Thread(target=run_blocking_task)
# Start the thread
thread.start()

scheduler.start()
