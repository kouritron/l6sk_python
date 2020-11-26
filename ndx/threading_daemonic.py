import threading
import time

# ======================================================================================================================
# ======================================================================================================================
def thread_entry():
    print("thread_entry() called.")
    raise Exception("Bad times")
    print("post exception. should never run.")


# ======================================================================================================================
# ======================================================================================================================
def main():
    print("main() called.")
    thread = threading.Thread(target=thread_entry, name='demo_thread')
    thread.daemon = True
    thread.start()

    print("main() sleep now.")
    time.sleep(1)
    print("main() finisehd.")



if '__main__' == __name__:
    main()
