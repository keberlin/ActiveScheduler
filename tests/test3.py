import logging
from time import sleep

from ..activescheduler import ActiveThread, scheduler

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def move_scara(seconds: float):
    logging.debug(f"move_scara: for {seconds} seconds")
    sleep(seconds)


ActiveThread(move_scara, 3)


scheduler.start()
