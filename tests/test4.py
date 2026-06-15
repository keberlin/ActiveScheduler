import logging
from datetime import timedelta

from activescheduler import ActivePeriodicTimer, ActiveTimer, scheduler

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class MyPeriodicTimer(ActivePeriodicTimer):
    def __init__(self, timeout: timedelta):
        super().__init__(timeout)

        self.count = 0

    def run(self):
        logging.info(f"MyPeriodicTimer ({self.count}) has fired..")
        self.count += 1


def timer_func():
    logging.info("my_timer_func has fired..")


count = 0


def periodic_timer_func():
    global count
    logging.info(f"periodic_timer_func ({count}) has fired..")
    count += 1
    if count > 5:
        exit(0)


ActiveTimer(timedelta(seconds=3), timer_func)
ActivePeriodicTimer(timedelta(seconds=2), periodic_timer_func)
MyPeriodicTimer(timedelta(seconds=1))

scheduler.start()
