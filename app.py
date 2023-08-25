import time
from io import BytesIO

from flask import Flask, send_file
from multiprocessing import shared_memory
from datetime import datetime, timedelta
import threading

app = Flask(__name__)

# Read the file content
with open("1000mb.bin", "rb") as file:
    file_data = file.read()

shared_memory_handle = None
last_access_time = None
cleanup_interval = 10  # seconds


def preload_file_to_shared_memory():
    # https://superfastpython.com/multiprocessing-sharedmemory/
    global shared_memory_handle, last_access_time
    if shared_memory_handle is None:
        # Create shared memory for the file
        shm = shared_memory.SharedMemory(create=True, size=len(file_data))
        shm.buf[:len(file_data)] = file_data
        shared_memory_handle = shm
        last_access_time = datetime.now()
    else:
        last_access_time = datetime.now()
    return shared_memory_handle


def cleanup_unused_shared_memory():
    # https://superfastpython.com/multiprocessing-sharedmemory/
    global shared_memory_handle, last_access_time
    while True:
        if last_access_time and (datetime.now() - last_access_time) > timedelta(seconds=cleanup_interval):
            if shared_memory_handle:
                shared_memory_handle.close()
                shared_memory_handle.unlink()
                shared_memory_handle = None
                last_access_time = None
        # Sleep for some time before checking again
        time.sleep(cleanup_interval)


cleanup_thread = threading.Thread(target=cleanup_unused_shared_memory)
cleanup_thread.daemon = True
cleanup_thread.start()


def send_file_using_io():
    return BytesIO(file_data)


@app.route('/get_file_io')
def get_file_io():
    return send_file(send_file_using_io(), mimetype='application/octet-stream')


@app.route('/get_file')
def get_file():
    shm = preload_file_to_shared_memory()
    # Wrap the SharedMemory object in a BytesIO object
    bytes_io = BytesIO(shm.buf)
    return send_file(bytes_io, mimetype='application/octet-stream')


if __name__ == '__main__':
    app.run(debug=True)
