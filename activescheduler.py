import logging
from datetime import datetime, timedelta
from enum import Enum
from threading import Condition, Event, Thread, current_thread
from typing import Any, Callable, List

logger = logging.getLogger()

#
# Active Scheduler
#


class ActiveObjectState(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    COMPLETED = "completed"


class ActiveScheduler:
    def __init__(self):
        self.cond: Condition = Condition()
        self.aobjects: List[ActiveObject] = []
        self.timers: List[ActiveTimer] = []
        self.thread_ident: int = current_thread().ident
        self.dump: Callable | None = None

    def set_dump(self, dump: Callable):
        self.dump = dump

    def start(self):
        while True:
            # If all active objects are idle then quit
            if all(ao.ao_status == ActiveObjectState.IDLE for ao in self.aobjects) and not self.timers:
                break
            self.process()

    def notify(self):
        logging.debug("notifying...")
        with self.cond:
            self.cond.notify_all()

    def process(self):
        # See if there are any active objects that have completed
        if not any(ao.ao_status == ActiveObjectState.COMPLETED for ao in self.aobjects):
            # Wait for an active object to fire
            if self.dump:
                self.dump()
            logging.debug("waiting for activity...")
            self.timers.sort(key=lambda x: x.expiry)  # TODO: Just get closest expiry time
            now = datetime.utcnow()
            timeout = (self.timers[0].expiry - now).total_seconds() if self.timers else None
            with self.cond:
                self.cond.wait(timeout)
        # Go through all timers and see if any have expired
        # TODO: Get highest priority completed AO
        # TODO: Only run timers and AOs with this priority
        now = datetime.utcnow()
        for timer in self.timers:
            if timer.expiry <= now:
                timer._run()
        # Go through all active objects and process any completed ones
        for ao in self.aobjects:
            if ao.ao_status == ActiveObjectState.COMPLETED:
                ao._run()


scheduler = ActiveScheduler()


#
# Active Objects
#
class ActiveObject:
    def __init__(self, priority=10):
        self.priority = priority

        self.ao_status = ActiveObjectState.ACTIVE  # Set to Active by default
        self.lock = Event()
        scheduler.aobjects.append(self)

    def __del__(self):
        logging.debug(f"deleting ActiveObject {self}")
        try:
            scheduler.aobjects.remove(self)
        except ValueError:
            logging.debug(f"ActiveObject {self} already removed!")
        scheduler.notify()

    def is_idle(self):
        return self.ao_status == ActiveObjectState.IDLE

    def is_active(self):
        return self.ao_status == ActiveObjectState.ACTIVE

    def cancel(self):
        """This may be called within a sub-thread."""
        logging.debug(f"cancelling ActiveObject {self}")
        self.ao_status = ActiveObjectState.IDLE
        scheduler.notify()

    def delete(self):
        self.cancel()
        del self

    def _run(self):
        """This will always be called within the main-thread."""
        assert self.ao_status == ActiveObjectState.COMPLETED, f"{self} is not active"
        self.ao_status = ActiveObjectState.ACTIVE
        logging.debug(f"running ActiveObject {self}")
        self.run(self.payload)
        self.lock.set()

    def run(self, payload: Any):
        """This will always be called within the main-thread."""
        assert False, "You need to define a run() function in your sub-class"

    def set_active(self):
        """This may be called within a sub-thread."""
        assert self.ao_status == ActiveObjectState.IDLE, f"{self} is not idle"
        logging.debug(f"setting ActiveObject {self} active")
        self.ao_status = ActiveObjectState.ACTIVE

    def complete(self, payload: Any = None):
        """This may be called within a sub-thread."""
        assert self.ao_status == ActiveObjectState.ACTIVE, f"{self} is not active"
        logging.debug(f"completing ActiveObject{self}")
        self.lock.clear()
        self.ao_status = ActiveObjectState.COMPLETED
        self.payload = payload
        if current_thread().ident != scheduler.thread_ident:
            scheduler.notify()
            self.lock.wait()


class ActiveThread(ActiveObject):
    def process(self):
        self.func(*self.nargs, **self.kwargs)
        self.complete()

    def __init__(self, func: Callable, *nargs, **kwargs):
        super().__init__()
        self.func = func
        self.nargs = nargs
        self.kwargs = kwargs

        thread = Thread(target=self.process)
        thread.start()
        thread.join()
        self.delete()

    def run(self, payload: Any):
        """This will always be called within the main-thread."""
        pass


#
# Active Timers
#


class ActiveTimer:
    def __init__(self, timeout: timedelta, func: Callable, *nargs, **kwargs):
        self.func = func
        self.nargs = nargs
        self.kwargs = kwargs

        now = datetime.utcnow()
        self.expiry = now + timeout
        scheduler.timers.append(self)

    def __del__(self):
        logging.debug(f"deleting ActiveTimer {self}")
        try:
            scheduler.timers.remove(self)
        except ValueError:
            logging.debug(f"ActiveTimer {self} already removed!")

    def delete(self):
        del self

    def _run(self):
        """This will always be called within the main-thread."""
        logging.debug(f"running ActiveTimer {self}")
        if self.func:
            self.func(*self.nargs, **self.kwargs)
        else:
            self.run()
        try:
            scheduler.timers.remove(self)
        except ValueError:
            logging.debug(f"ActiveTimer {self} already removed!")


class ActivePeriodicTimer(ActiveTimer):
    def __init__(self, timeout: timedelta, func=None, *nargs, **kwargs):
        super().__init__(timeout, func, *nargs, **kwargs)

        self.period = timeout

    def _run(self):
        """This will always be called within the main-thread."""
        logging.debug(f"running ActivePeriodicTimer {self}")
        if self.func:
            self.func(*self.nargs, **self.kwargs)
        else:
            self.run()
        self.expiry += self.period
