from threading import Event, Thread
from typing import List


class Threader(object):
    def __init__(self):
        self._stop_event = Event()
        self._threads: List[Thread] = []

    def _create_threads(self):
        raise NotImplementedError('_create_threads needs to be implemented')

    def _before_start(self):
        raise NotImplementedError('_before_start needs to be implemented')

    def _after_stop(self):
        raise NotImplementedError('_before_start needs to be implemented')

    def start(self):
        self._stop_event.clear()

        if len(self._threads) == 0:
            self._create_threads()

            self._before_start()

            for thread in self._threads:
                thread.start()

    def stop(self):
        self._stop_event.set()

        if len(self._threads) > 0:
            for thread in self._threads:
                thread.join()

            self._threads.clear()

            self._after_stop()
