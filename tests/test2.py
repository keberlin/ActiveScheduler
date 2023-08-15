from threading import Thread


def my_func():
    try:
        print("calling my_func..")
        raise Exception
    except Exception as e:
        print(f"Exception 0 thrown {e}")
        raise


try:
    thread1 = Thread(target=my_func)
except Exception as e:
    print(f"Exception 1 thrown {e}")
try:
    thread1.start()
except Exception as e:
    print(f"Exception 2 thrown {e}")
try:
    thread1.join()
except Exception as e:
    print(f"Exception 3 thrown {e}")
