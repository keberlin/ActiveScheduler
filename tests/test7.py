import logging
import os
from datetime import timedelta

from test4 import MyActiveTimer, MyPeriodicTimer
from test6 import FileReaderBlocking

from activescheduler import ActiveBase, ActiveNotifier, scheduler

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PATH = os.path.dirname(__file__)


class Controller(ActiveNotifier):

    def __init__(self):
        FNAME = "data.txt"

        fname = os.path.join(PATH, FNAME)

        # Setup active objects
        self.reader = FileReaderBlocking(fname, self)

        # Setup active timers
        timers = []
        timers.append(MyActiveTimer(timedelta(seconds=3), self))
        for i in range(4):
            timers.append(MyPeriodicTimer(timedelta(seconds=1), self))

    def notify_postrun(self, ao: ActiveBase):
        """This will always be called within the main-thread."""
        logger.info(f"Controller: ActiveBase {ao} has run..")


if __name__ == "__main__":

    controller = Controller()

    scheduler.start()
