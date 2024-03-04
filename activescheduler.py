import logging
from datetime import datetime, timedelta
from enum import Enum
from threading import Condition, Event, Thread, current_thread
from typing import Callable, List


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

    def process(self):
        # See if there are any active objects that have completed
        if not any(ao.ao_status == ActiveObjectState.COMPLETED for ao in self.aobjects):
            # Wait for an active object to fire
            if self.dump:
                self.dump()
            logging.debug("waiting for activity...")
            self.timers.sort(key=lambda x: x.expiry)
            now = datetime.utcnow()
            timeout = (self.timers[0].expiry - now).total_seconds() if self.timers else None
            with self.cond:
                self.cond.wait(timeout)
            assert any(ao.ao_status == ActiveObjectState.COMPLETED for ao in self.aobjects) or self.timers
        # Go through all timers and see if any have expired
        now = datetime.utcnow()
        for timer in self.timers[:]:
            if timer.expiry <= now:
                self.timers.remove(timer)
                timer._run()
        # Go through all active objects and process any completed ones
        for ao in self.aobjects:
            if ao.ao_status == ActiveObjectState.COMPLETED:
                ao.ao_status = ActiveObjectState.IDLE
                ao._run()


scheduler = ActiveScheduler()


class ActiveObject:
    def __init__(self):
        self.ao_status = ActiveObjectState.IDLE
        scheduler.aobjects.append(self)
        self.lock = Event()

    def is_idle(self):
        return self.ao_status == ActiveObjectState.IDLE

    def is_active(self):
        return self.ao_status == ActiveObjectState.ACTIVE

    def cancel(self):
        self.ao_status = ActiveObjectState.IDLE

    def delete(self):
        scheduler.aobjects.remove(self)
        del self

    def _run(self):
        """This will always be called within the main-thread."""
        logging.debug(f"running {self}")
        self.run()
        self.lock.set()

    def run(self):
        """This will always be called within the main-thread."""
        assert False, "You need to define a run() function in your sub-class"

    def set_active(self):
        """This must be called within the main-thread."""
        assert self.ao_status == ActiveObjectState.IDLE, f"{self} is not idle"
        assert current_thread().ident == scheduler.thread_ident, f"{self} set_active being called on a sub-thread"
        logging.debug(f"setting {self} active")
        self.ao_status = ActiveObjectState.ACTIVE

    def complete(self):
        """This may be called within a sub-thread."""
        assert self.ao_status == ActiveObjectState.ACTIVE, f"{self} is not active"
        logging.debug(f"completing {self}")
        self.ao_status = ActiveObjectState.COMPLETED
        self.lock.clear()
        with scheduler.cond:
            scheduler.cond.notify_all()
        if current_thread().ident != scheduler.thread_ident:
            self.lock.wait()


class ActiveTimer:
    def __init__(self, timeout: timedelta, func: Callable, *nargs, **kwargs):
        self.func = func
        self.nargs = nargs
        self.kwargs = kwargs
        now = datetime.utcnow()
        self.expiry = now + timeout
        scheduler.timers.append(self)

    def delete(self):
        scheduler.timers.remove(self)
        del self

    def _run(self):
        """This will always be called within the main-thread."""
        if self.func:
            self.func(*self.nargs, **self.kwargs)
        del self


class ActivePeriodicTimer(ActiveTimer):
    def __init__(self, timeout: timedelta, func=None, *nargs, **kwargs):
        super().__init__(timeout, func, *nargs, **kwargs)
        self.period = timeout

    def _run(self):
        """This will always be called within the main-thread."""
        self.expiry += self.period
        scheduler.timers.append(self)
        if self.func:
            self.func(*self.nargs, **self.kwargs)
        else:
            self.run()


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
        self.set_active(wait=True)
        thread.join()
        self.delete()

    def _run(self):
        """This will always be called within the main-thread."""
        pass
