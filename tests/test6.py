import logging
import os
from time import sleep

from activescheduler import ActiveNotifier, ActiveObject, ActiveThread, scheduler

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

PATH = os.path.dirname(__file__)

CHUNK_SIZE = 100


class FileReaderBlocking(ActiveThread):

    def __init__(self, fname: str, notifier: ActiveNotifier = None):
        super().__init__(notifier)

        # Initialise
        self.file = open(fname, "r")
        self.contents = ""

        # The ActiveThread automatically kicks off the process() function within a sub-thread

    def run(self):
        """This will always be called within the main-thread."""
        logging.info(f"FileReaderBlocking: has run..")
        self.contents += self.payload
        sleep(0.3)

    def process(self):
        """Read the file contents using chunks within a sub-thread."""

        while True:
            # Read the next chunk
            data = self.file.read(CHUNK_SIZE)
            if not data:
                break
            self.complete(data)  # This won't return until self.run() has been called


if __name__ == "__main__":

    FNAME = "data.txt"

    fname = os.path.join(PATH, FNAME)

    # Setup active objects
    reader = FileReaderBlocking(fname)

    scheduler.start()

    # Check that the reader has read the entire contents of FNAME
    with open(fname, "r") as f:
        assert reader.contents == f.read()
