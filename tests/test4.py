import logging
from datetime import timedelta

from activescheduler import ActiveNotifier, ActivePeriodicTimer, ActiveTimer, scheduler

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class MyActiveTimer(ActiveTimer):
    def run(self):
        """This will always be called within the main-thread."""
        logging.info(f"MyActiveTimer: has run..")


class MyPeriodicTimer(ActivePeriodicTimer):
    def __init__(self, timeout: timedelta, notifier: ActiveNotifier = None):
        super().__init__(timeout, notifier)

        self.count = 0

    def run(self):
        """This will always be called within the main-thread."""
        self.count += 1
        logging.info(f"MyPeriodicTimer: has run with count {self.count}..")
        if self.count >= 5:
            self.cancel()


if __name__ == "__main__":

    timers = []
    timers.append(MyActiveTimer(timedelta(seconds=3)))
    for i in range(4):
        timers.append(MyPeriodicTimer(timedelta(seconds=1)))

    scheduler.start()
