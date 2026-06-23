import logging
from datetime import datetime, timedelta
from enum import Enum
from threading import Condition, Event, Thread, current_thread
from typing import Any, Callable, List

logger = logging.getLogger()

#
# Active Scheduler
#


class ActiveBase:
    pass


class ActiveNotifier:
    def notify_set_active(self, ao: ActiveBase):
        pass

    def notify_cancel(self, ao: ActiveBase):
        pass

    def notify_prerun(self, ao: ActiveBase):
        pass

    def notify_postrun(self, ao: ActiveBase):
        pass


class ActiveState(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    COMPLETED = "completed"


DEFAULT_PRIORITY = 10


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
            if all(ao.ao_status == ActiveState.IDLE for ao in self.aobjects) and not self.timers:
                break
            self.process()

    def notify(self):
        logging.debug("notifying...")
        with self.cond:
            self.cond.notify_all()

    def process(self):
        # See if there are any active objects that have completed
        if not any(ao.ao_status == ActiveState.COMPLETED for ao in self.aobjects):
            # Wait for an active object to fire
            if self.dump:
                self.dump()
            logging.debug("waiting for activity...")
            if self.timers:
                expiry = min([v.expiry for v in self.timers])
                now = datetime.utcnow()
                timeout = (expiry - now).total_seconds()
                timeout = max(timeout, 0)
            else:
                timeout = None
            with self.cond:
                self.cond.wait(timeout)
        # Go through all timers and see if any have expired
        # TODO: Get highest priority completed AO
        # TODO: Only run timers and AOs with this priority
        now = datetime.utcnow()
        for timer in self.timers[:]:  # Take a copy of the list just in case timers get removed part way through
            if timer.expiry <= now:
                timer.ao_status = ActiveState.COMPLETED
                timer._run()
        # Go through all active objects and process any completed ones
        for ao in self.aobjects[:]:  # Take a copy of the list just in case AOs get removed part way through
            if ao.ao_status == ActiveState.COMPLETED:
                ao._run()


scheduler = ActiveScheduler()


class ActiveBase:
    def __init__(self, notifier: ActiveNotifier = None, priority=10):
        self.notifier = notifier
        self.priority = priority

        self.ao_status = ActiveState.ACTIVE  # Set to Active by default

    def _run(self):
        """This will always be called within the main-thread."""
        logging.debug(f"running ActiveBase {self}")
        assert self.ao_status == ActiveState.COMPLETED, f"{self} is not active"
        self.ao_status = ActiveState.ACTIVE

        if self.notifier:
            self.notifier.notify_prerun(self)
        self.run()
        if self.notifier:
            self.notifier.notify_postrun(self)

    def is_idle(self):
        return self.ao_status == ActiveState.IDLE

    def is_active(self):
        return self.ao_status == ActiveState.ACTIVE

    def set_active(self):
        """This may be called within a sub-thread."""
        assert self.ao_status == ActiveState.IDLE, f"{self} is not idle"
        logging.debug(f"setting ActiveBase {self} active")
        self.ao_status = ActiveState.ACTIVE
        if self.notifier:
            self.notifier.notify_set_active(self)

    def cancel(self):
        """This may be called within a sub-thread."""
        logging.debug(f"cancelling ActiveBase {self}")
        self.ao_status = ActiveState.IDLE
        if self.notifier:
            self.notifier.notify_cancel(self)
        scheduler.notify()


#
# Active Objects
#


class ActiveObject(ActiveBase):
    def __init__(self, notifier: ActiveNotifier = None, priority: int = DEFAULT_PRIORITY):
        super().__init__(notifier, priority)

        self.payload = None
        self.lock = Event()
        scheduler.aobjects.append(self)

    def __del__(self):
        logging.debug(f"deleting ActiveObject {self}")
        self.cancel()

    def _run(self):
        """This will always be called within the main-thread."""
        logging.debug(f"running ActiveObject {self}")

        super()._run()

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
        assert self.ao_status == ActiveState.ACTIVE, f"{self} is not active"
        logging.debug(f"completing ActiveObject {self}")
        self.lock.clear()
        self.ao_status = ActiveState.COMPLETED
        self.payload = payload
        if current_thread().ident != scheduler.thread_ident:
            scheduler.notify()
            self.lock.wait()

    def run(self, payload: Any):
        """This will always be called within the main-thread."""
        assert False, "You need to define a run() function in your sub-class"


#
# Active Timers
#


class ActivePeriodicTimer(ActiveBase):
    def __init__(self, timeout: timedelta, notifier: ActiveNotifier = None, priority: int = DEFAULT_PRIORITY):
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

        super()._run()

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


#
# Utilities
#


class ActiveOneShotTimer(ActiveTimer):
    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__(timedelta(0))

        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.func(*self.args, **self.kwargs)


class ActiveThread(ActiveObject):

    def __init__(self, notifier: ActiveNotifier = None, priority: int = DEFAULT_PRIORITY):
        super().__init__(notifier, priority)

        # Automatically call the _start() function
        self.timer = ActiveOneShotTimer(self._start)

    def _start(self):
        del self.timer

        # Create a new sub-thread
        self.thread = Thread(target=self._process)
        # Start _process() within this thread
        self.thread.start()

    def _process(self):
        self.process()

        self.cancel()
        del self
