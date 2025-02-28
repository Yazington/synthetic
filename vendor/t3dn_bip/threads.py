# coding: utf-8
import bpy
import bpy.utils.previews
from queue import Queue
from threading import Thread, Event
from time import time
from traceback import print_exc
from multiprocessing import cpu_count
from .utils import load_file, tag_redraw
from . import settings
_pending = 0
_queue_read = Queue()
_queue_emplace = Queue()
_thread_stop_signal = None

def _read_thread(stop_signal: Event):
    """Read image data in the background."""
    while not stop_signal.is_set():
        try:
            results = _queue_read.get(block=True, timeout=1.0)
            (collection, name, filepath, max_size, abort_signal) = results
        except:
            continue
        data = None
        if not abort_signal.is_set():
            try:
                data = load_file(filepath, max_size)
            except:
                print_exc()
        _queue_emplace.put((collection, name, data, abort_signal))

def _emplace_timer():
    """Emplaces pixels into the preview object. Runs on the main thread."""
    global _pending
    global _thread_stop_signal
    now = time()
    delay = 0.1
    redraw = False
    while time() - now < 0.1:
        try:
            results = _queue_emplace.get(block=False)
            (collection, name, data, abort_signal) = results
        except:
            break
        _pending -= 1
        if not abort_signal.is_set() and name in collection:
            try:
                preview = collection[name]
                preview.icon_size = data['icon_size']
                preview.icon_pixels = data['icon_pixels']
                preview.image_size = data['image_size']
                preview.image_pixels = data['image_pixels']
            except:
                print_exc()
            else:
                redraw = True
    else:
        delay = 0.01
    if redraw:
        tag_redraw()
    if not _pending:
        if _thread_stop_signal:
            _thread_stop_signal.set()
            _thread_stop_signal = None
        delay = None
    return delay

def load_async(collection: bpy.utils.previews.ImagePreviewCollection, name: str, filepath: str, max_size: tuple, abort_signal: Event):
    """Load image asynchronously. Needs to be called on the main thread."""
    global _pending
    global _thread_stop_signal
    _pending += 1
    _queue_read.put((collection, name, filepath, max_size, abort_signal))
    if not _thread_stop_signal:
        _thread_stop_signal = Event()
        for _ in range(max(min(cpu_count(), settings.MAX_THREADS), 1)):
            thread = Thread(target=_read_thread, args=(_thread_stop_signal,))
            thread.start()
    if not bpy.app.timers.is_registered(_emplace_timer):
        bpy.app.timers.register(_emplace_timer, persistent=True)
