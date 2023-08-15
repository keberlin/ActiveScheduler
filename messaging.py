import logging
from dataclasses import dataclass
from queue import Empty, Queue
from random import randint
from threading import Event, Thread
from time import sleep
from typing import Any, Callable, Dict, List

from activescheduler import ActiveObject, scheduler

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


@dataclass
class ThreadResponse:
    def __init__(self):
        self._lock = Event()

    def wait(self):
        self._lock.wait()

    @property
    def response(self):
        return self._response

    @response.setter
    def response(self, value: Any):
        self._response = value
        self._lock.set()


@dataclass
class Message:
    function: Callable[[str, Any], None]
    args: List
    kwargs: Dict
    response: ThreadResponse | None


class Messaging(ActiveObject):
    def __init__(self):
        super().__init__()
        self.queue = Queue()
        self.set_active()

    def run(self):
        """This will always be called within the main-thread."""
        while True:
            try:
                message = self.queue.get()
                result = message.function(*message.args, **message.kwargs)
                if message.response:
                    message.response.response = result
            except Empty:
                break
        self.set_active()

    def message(self, func: Callable, *args, **kwargs):
        """This may be called within a sub-thread."""
        self.queue.put(Message(func, args, kwargs, None))
        if self.is_active():
            self.complete()

    def message_with_response(self, func: Callable, *args, **kwargs):
        """This may be called within a sub-thread."""
        response = ThreadResponse()
        self.queue.put(Message(func, args, kwargs, response))
        if self.is_active():
            self.complete()
        response.wait()
        return response.response


messaging = Messaging()

if __name__ == "__main__":

    def handler(action: str, param1: str, param2: str, param3: str):
        logging.info(f"message handler: {action} {param1} {param2} {param3}")
        return action

    def process(*args: List, **kwargs: Dict):
        sleep(randint(1, 5))
        logging.info(f"message: {args} {kwargs}")
        result = messaging.message_with_response(handler, *args, **kwargs)
        logging.info(f"result: {result}")

    for i in range(5):
        thread = Thread(
            target=process,
            args=[f"Action {i}", "Param 1", "Param 2"],
            kwargs={"param3": "Param 3"},
        )
        thread.start()

    scheduler.start()
