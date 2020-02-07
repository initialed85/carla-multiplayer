import datetime
import time
from threading import Event, Thread
from typing import Optional, Union


class _LooperMixIn(object):
    def __init__(self):
        self._stop_event = Event()
        self._thread: Optional[Thread] = None

    def _before_loop(self):
        pass

    def _before_work(self):
        pass

    def _work(self):
        raise NotImplementedError('_work needs to be implemented')

    def _after_work(self):
        pass

    def _after_loop(self):
        pass

    def _loop(self):
        raise NotImplementedError('_work needs to be implemented')

    def start(self):
        self._stop_event.clear()

        if self._thread is None:
            self._thread = Thread(target=self._loop)
            self._thread.start()

    def stop(self):
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join()
            self._thread = None


class Looper(_LooperMixIn):
    def _loop(self):
        if self._before_loop() is True:
            return

        while not self._stop_event.is_set():
            if self._before_work() is True:
                continue

            if self._work() is True:
                continue

            if self._after_work() is True:
                continue

        if self._after_loop() is True:
            return


class TimedLooper(_LooperMixIn):
    def __init__(self, period: Union[float, int]):
        super().__init__()

        self._period: float = period
        self._period_delta: datetime.timedelta = datetime.timedelta(seconds=self._period)

    def _sleep(self, work_started: datetime.datetime):
        work_finished = datetime.datetime.now()

        work_should_have_finished = work_started + self._period_delta
        if work_finished >= work_should_have_finished:
            return

        time.sleep((work_should_have_finished - work_finished).total_seconds())

    def _loop(self):
        if self._before_loop() is False:
            return

        while not self._stop_event.is_set():
            work_started = datetime.datetime.now()
            if self._before_work() is False:
                self._sleep(work_started)
                continue

            if self._work() is False:
                self._sleep(work_started)
                continue

            if self._after_work() is False:
                self._sleep(work_started)
                continue

            self._sleep(work_started)

        if not self._after_loop():
            return
