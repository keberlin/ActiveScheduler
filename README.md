# ActiveScheduler

`ActiveScheduler` is a small Python event-driven framework inspired by Symbian's active scheduler model. It gives you a cooperative scheduler that runs callbacks on a single scheduler thread while allowing worker threads and timers to signal work completion back into that thread.

The repository currently exposes two main modules:

- `activescheduler.py` - the scheduler, active object, thread, and timer primitives.
- `messaging.py` - a simple message queue helper for marshalling work onto the scheduler thread.

## Installation

### Requirements

- Python 3.10 or newer

### Local setup

From the repository root:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .
```

If you only want to run the examples without installing the project as a package, you can also run the scripts directly from the repository root.

## What it does

The framework is built around a few core ideas:

- **Active objects** represent units of work that become runnable when they complete or are triggered.
- **Timers** schedule one-shot or periodic callbacks on the scheduler thread.
- **Worker threads** can perform blocking work and then safely hand results back to the scheduler thread.
- **Notifier hooks** let you observe lifecycle events such as activation, cancellation, and execution.

This makes the project useful as a lightweight template for:

- event-driven applications,
- cooperative task orchestration,
- thread-to-main-thread handoff patterns,
- embedded-style scheduling experiments in Python.

## Core types

### `ActiveScheduler`

The global `scheduler` instance coordinates active objects and timers.

- `scheduler.start()` enters the event loop.
- `scheduler.notify()` wakes the scheduler when background work completes.
- The loop exits when all active objects are idle and there are no timers left.

### `ActiveObject`

Subclass `ActiveObject` when some external activity will eventually produce a result that should be handled on the scheduler thread.

Key behavior:

- `complete(payload)` marks the object as completed.
- `run()` is invoked by the scheduler thread.
- `cancel()` removes the object from scheduling.

If `complete()` is called from a worker thread, it waits until the scheduler has executed the matching `run()` call. That gives you a simple synchronization point between worker logic and scheduler-thread logic.

### `ActiveThread`

Subclass `ActiveThread` when you want blocking or long-running work to happen in a background thread while results are consumed on the scheduler thread.

- Put background work in `process()`.
- Call `complete(payload)` from `process()` when a chunk of work is ready.
- Handle the payload in `run()` on the scheduler thread.

### `ActiveTimer` and `ActivePeriodicTimer`

Use timers when work should happen after a delay or on a fixed interval.

- `ActiveTimer` runs once, then removes itself.
- `ActivePeriodicTimer` keeps rescheduling itself until you call `cancel()`.

### `ActiveNotifier`

Implement `ActiveNotifier` when you want hooks around object lifecycle events:

- `notify_set_active()`
- `notify_cancel()`
- `notify_prerun()`
- `notify_postrun()`

## Quick start

### Example: one-shot timer

```python
from datetime import timedelta

from activescheduler import ActiveTimer, scheduler


class HelloTimer(ActiveTimer):
    def run(self):
        print("timer fired")


HelloTimer(timedelta(seconds=1))
scheduler.start()
```

### Example: non-blocking active object

This pattern mirrors the file-reading example in `tests/test5.py`.

```python
from activescheduler import ActiveObject, scheduler


class Stepper(ActiveObject):
    def __init__(self, values):
        super().__init__()
        self.values = list(values)
        self.results = []
        self.next_step()

    def next_step(self):
        if not self.values:
            self.cancel()
            return
        self.complete(self.values.pop(0))

    def run(self):
        self.results.append(self.payload * 2)
        self.next_step()


stepper = Stepper([1, 2, 3])
scheduler.start()
print(stepper.results)
```

### Example: messaging helper

`messaging.py` includes a `Messaging` active object that lets background threads execute functions on the scheduler thread.

Typical usage:

```python
from messaging import messaging


def handler(action, value):
    print(f"handling {action}: {value}")
    return value * 2


result = messaging.message_with_response(handler, "update", 21)
print(result)
```

## Repository layout

- `activescheduler.py` - scheduler primitives and base classes.
- `messaging.py` - queued function dispatch via the scheduler thread.
- `tests/test4.py` - timer examples.
- `tests/test5.py` - non-blocking active object example.
- `tests/test6.py` - blocking file-reader example using a worker thread.
- `tests/test7.py` - notifier/controller example.

The `tests/` directory currently acts more like a set of runnable example scripts than a conventional automated test suite.

## Running the examples

From the repository root:

```bash
python tests/test4.py
python tests/test5.py
python tests/test6.py
python tests/test7.py
python messaging.py
```

## Development notes

- The project metadata lives in `pyproject.toml`.
- The published package metadata is aligned to the `ActiveScheduler` project name.
- The codebase is intentionally small and centered around the two top-level modules.

## When to use this project

`ActiveScheduler` is a good fit when you want:

- explicit scheduler-thread execution,
- simple coordination between timers, background threads, and callbacks,
- a lightweight alternative to a larger async framework,
- a reference implementation of an active-object style design in Python.

It is less suitable when you need:

- high-throughput async I/O,
- process supervision,
- distributed scheduling,
- a production-ready task queue out of the box.
