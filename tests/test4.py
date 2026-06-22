import logging
from datetime import timedelta

from activescheduler import ActivePeriodicTimer, ActiveTimer, scheduler

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class MyActiveTimer(ActiveTimer):
    def run(self):
        logging.info(f"MyActiveTimer has fired..")


class MyPeriodicTimer(ActivePeriodicTimer):
    def __init__(self, timeout: timedelta):
        super().__init__(timeout)

        self.count = 0

    def run(self):
        self.count += 1
        logging.info(f"MyPeriodicTimer has fired with count {self.count}..")
        if self.count >= 5:
            self.cancel()


timers = []
timers.append(MyActiveTimer(timedelta(seconds=3)))
for i in range(4):
    timers.append(MyPeriodicTimer(timedelta(seconds=1)))

scheduler.start()
