from multiprocessing import Lock
from random import randint
from threading import Thread, current_thread
from time import sleep


def thread_safe(lock):
    def func_wrapper(func):
        def wrapper(*args, **kwargs):
            lock.acquire()  # this will block until the mutex lock has been acquired
            ret = func(*args, **kwargs)
            lock.release()  # this will release the mutex lock and allow other functions to be called
            return ret

        return wrapper

    return func_wrapper


def run_in_thread(func, *args, **kwargs):
    thread = Thread(target=func, args=args, kwargs=kwargs)
    thread.start()
    return thread


lock = Lock()


@thread_safe(lock)
def my_thread_safe_func():
    print(f"entry into thread {current_thread()}..", flush=True)
    sleep(randint(1, 5))
    print(f"exit from thread {current_thread()}..", flush=True)


threads = []
for _ in range(3):
    threads.append(run_in_thread(my_thread_safe_func))

for thread in threads:
    thread.join()
