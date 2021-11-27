# With function to block print calls
import contextlib
import os, sys

@contextlib.contextmanager
def blockprint():
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')

    yield

    sys.stdout.close()
    sys.stdout = original_stdout
