import logging
from datetime import timedelta

from ..activescheduler import ActivePeriodicTimer, ActiveTimer, scheduler

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class MyPeriodicTimer(ActivePeriodicTimer):
    def run(self):
        logging.info("MyPeriodicTimer has fired..")


def my_timer_func():
    logging.info("my_timer_func has fired..")


count = 10


def my_periodic_timer_func():
    global count
    logging.info("my_periodic_timer_func has fired..")
    count -= 1
    if not count:
        exit(0)


ActiveTimer(timedelta(seconds=3), my_timer_func)
ActivePeriodicTimer(timedelta(seconds=2), my_periodic_timer_func)
MyPeriodicTimer(timedelta(seconds=1))

scheduler.start()
