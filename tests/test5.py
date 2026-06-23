import logging
import os

from activescheduler import ActiveObject, scheduler

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

PATH = os.path.dirname(__file__)

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

    def run(self):
        self.contents += self.payload

        # Next chunk
        self.read()


if __name__ == "__main__":

    FNAME = "data.txt"

    fname = os.path.join(PATH, FNAME)

    # Non-blocking
    reader = FileReaderNonBlocking(fname)

    scheduler.start()

    # Check that the reader has read the entire contents of fname
    with open(fname, "r") as f:
        assert reader.contents == f.read()
