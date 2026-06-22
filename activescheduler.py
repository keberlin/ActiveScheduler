import logging
from datetime import datetime, timedelta
from enum import Enum
from threading import Condition, Event, Thread, current_thread
from typing import Any, Callable, List

logger = logging.getLogger()

#
# Active Scheduler
#


class ActiveObject:
    pass


class AONotifier:
    def notify_set_active(self, ao: ActiveObject):
        pass

    def notify_cancel(self, ao: ActiveObject):
        pass

    def notify_prerun(self, ao: ActiveObject, data: Any = None):
        pass

    def notify_postrun(self, ao: ActiveObject, data: Any = None):
        pass


class AOState(Enum):
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
            if all(ao.ao_status == AOState.IDLE for ao in self.aobjects) and not self.timers:
                break
            self.process()

    def notify(self):
        logging.debug("notifying...")
        with self.cond:
            self.cond.notify_all()

    def process(self):
        # See if there are any active objects that have completed
        if not any(ao.ao_status == AOState.COMPLETED for ao in self.aobjects):
            # Wait for an active object to fire
            if self.dump:
                self.dump()
            logging.debug("waiting for activity...")
            self.timers.sort(key=lambda x: x.expiry)  # TODO: Just get closest expiry time
            now = datetime.utcnow()
            timeout = (self.timers[0].expiry - now).total_seconds() if self.timers else None  # TODO: ensure not -ve
            with self.cond:
                self.cond.wait(timeout)
        # Go through all timers and see if any have expired
        # TODO: Get highest priority completed AO
        # TODO: Only run timers and AOs with this priority
        now = datetime.utcnow()
        for timer in self.timers[:]:  # Take a copy of the list just in case timers get removed part way through
            if timer.expiry <= now:
                timer._run()
        # Go through all active objects and process any completed ones
        for ao in self.aobjects[:]:  # Take a copy of the list just in case AOs get removed part way through
            if ao.ao_status == AOState.COMPLETED:
                ao._run()


scheduler = ActiveScheduler()


class AOBase:
    def __init__(self, notifier: AONotifier = None, priority=10):
        self.notifier = notifier
        self.priority = priority

        self.ao_status = AOState.ACTIVE  # Set to Active by default

    def is_idle(self):
        return self.ao_status == AOState.IDLE

    def is_active(self):
        return self.ao_status == AOState.ACTIVE

    def set_active(self):
        """This may be called within a sub-thread."""
        assert self.ao_status == AOState.IDLE, f"{self} is not idle"
        logging.debug(f"setting AOBase {self} active")
        self.ao_status = AOState.ACTIVE
        if self.notifier:
            self.notifier.notify_set_active(self)

    def cancel(self):
        """This may be called within a sub-thread."""
        logging.debug(f"cancelling AOBase {self}")
        self.ao_status = AOState.IDLE
        if self.notifier:
            self.notifier.notify_cancel(self)
        scheduler.notify()


#
# Active Objects
#
class ActiveObject(AOBase):
    def __init__(self, notifier: AONotifier = None, priority=10):
        super().__init__(notifier, priority)

        self.payload = None
        self.lock = Event()
        scheduler.aobjects.append(self)

    def __del__(self):
        logging.debug(f"deleting ActiveObject {self}")
        self.cancel()

    def _run(self):
        """This will always be called within the main-thread."""
        assert self.ao_status == AOState.COMPLETED, f"{self} is not active"
        self.ao_status = AOState.ACTIVE
        logging.debug(f"running ActiveObject {self}")

        if self.notifier:
            self.notifier.notify_prerun(self, self.payload)
        self.run(self.payload)
        if self.notifier:
            self.notifier.notify_postrun(self, self.payload)

        self.lock.set()

    def cancel(self):
        logging.debug(f"cancelling ActiveObject {self}")
        try:
            scheduler.aobjects.remove(self)
        except ValueError:
            pass
        super().cancel()

    def complete(self, payload: Any = None):
        """This may be called within a sub-thread."""
        assert self.ao_status == AOState.ACTIVE, f"{self} is not active"
        logging.debug(f"completing ActiveObject {self}")
        self.lock.clear()
        self.ao_status = AOState.COMPLETED
        self.payload = payload
        if current_thread().ident != scheduler.thread_ident:
            scheduler.notify()
            self.lock.wait()

    def run(self, payload: Any):
        """This will always be called within the main-thread."""
        assert False, "You need to define a run() function in your sub-class"


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


class ActivePeriodicTimer(AOBase):
    def __init__(self, timeout: timedelta, notifier: AONotifier = None, priority=10):
        super().__init__(notifier, priority)

        self.period = timeout

        now = datetime.utcnow()
        self.expiry = now + timeout

        scheduler.timers.append(self)

    def __del__(self):
        self.cancel()

    def _run(self):
        """This will always be called within the main-thread."""
        logging.debug(f"running ActivePeriodicTimer {self}")
        self.expiry += self.period

        if self.notifier:
            self.notifier.notify_prerun(self)
        self.run()
        if self.notifier:
            self.notifier.notify_postrun(self)

    def cancel(self):
        logging.debug(f"cancelling ActivePeriodicTimer {self}")
        try:
            scheduler.timers.remove(self)
        except ValueError:
            pass
        super().cancel()

    def run(self, payload: Any):
        """This will always be called within the main-thread."""
        assert False, "You need to define a run() function in your sub-class"


class ActiveTimer(ActivePeriodicTimer):

    def _run(self):
        """This will always be called within the main-thread."""
        logging.debug(f"running ActiveTimer {self}")
        super()._run()

        self.cancel()

        del self
