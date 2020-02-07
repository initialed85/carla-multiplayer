import time
import unittest
from threading import Thread

from mock import Mock

from .threader import Threader


class ThreaderImplementation(Threader):
    def __init__(self):
        super().__init__()

        self.mock_1 = Mock()
        self.mock_2 = Mock()

    def _work_1(self):
        while not self._stop_event.is_set():
            self.mock_1.work()
            time.sleep(0.1)

    def _work_2(self):
        while not self._stop_event.is_set():
            self.mock_2.work()
            time.sleep(0.1)

    def _create_threads(self):
        self._threads = [
            Thread(target=self._work_1),
            Thread(target=self._work_2),
        ]

    def _before_start(self):
        self.mock_1.before_start()
        self.mock_2.before_start()

    def _after_stop(self):
        self.mock_1.after_stop()
        self.mock_2.after_stop()


class ThreaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = ThreaderImplementation()
        self.subject.start()

    def tearDown(self) -> None:
        self.subject.stop()

    def test_lifecycle(self):
        self.subject.start()
        time.sleep(1)
        self.subject.stop()

        for mock in [self.subject.mock_1, self.subject.mock_2]:
            self.assertEqual(1, len(mock.before_start.mock_calls))
            self.assertGreaterEqual(len(mock.work.mock_calls), 1)
            self.assertEqual(1, len(mock.after_stop.mock_calls))
