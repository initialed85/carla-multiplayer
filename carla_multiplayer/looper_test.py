import datetime
import time
import unittest
from typing import List

from mock import Mock

from .looper import Looper, TimedLooper


class ImplementationMixIn(object):
    mock: Mock
    work_timestamps: List[datetime.datetime]

    def _before_loop(self):
        self.mock.before_loop()

        return True

    def _before_work(self):
        self.mock.before_work()

        return True

    def _work(self):
        self.mock.work()
        self.work_timestamps += [datetime.datetime.now()]

        time.sleep(0.1)

        return True

    def _after_work(self):
        self.mock.after_work()

        return True

    def _after_loop(self):
        self.mock.after_loop()

        return True


class LooperImplementation(ImplementationMixIn, Looper):
    def __init__(self):
        super().__init__()

        self.mock = Mock()
        self.work_timestamps = []


class TimedLooperImplementation(ImplementationMixIn, TimedLooper):
    def __init__(self, period: float):
        super().__init__(
            period=period
        )

        self.mock = Mock()
        self.work_timestamps = []


def start_stop_and_make_assertions(self):
    self.subject.start()
    time.sleep(1.0)
    self.subject.stop()

    self.assertEqual(1, len(self.subject.mock.before_loop.mock_calls))
    self.assertGreaterEqual(len(self.subject.mock.before_loop.mock_calls), 1)
    self.assertGreaterEqual(len(self.subject.mock.before_work.mock_calls), 1)
    self.assertGreaterEqual(len(self.subject.mock.work.mock_calls), 1)
    self.assertGreaterEqual(len(self.subject.mock.after_work.mock_calls), 1)
    self.assertGreaterEqual(len(self.subject.mock.after_loop.mock_calls), 1)


class LooperTest(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = LooperImplementation()
        self.subject.start()

    def tearDown(self) -> None:
        self.subject.stop()

    def test_lifecycle(self):
        start_stop_and_make_assertions(self)


class TimedLooperTest(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = TimedLooperImplementation(
            period=0.2
        )
        self.subject.start()

    def tearDown(self) -> None:
        self.subject.stop()

    def test_lifecycle(self):
        start_stop_and_make_assertions(self)

        deltas = []
        for i in range(1, len(self.subject.work_timestamps)):
            a = self.subject.work_timestamps[i - 1]
            b = self.subject.work_timestamps[i]

            deltas += [(b - a).total_seconds()]

        average_frequency = sum(deltas) / len(deltas)

        self.assertAlmostEqual(
            0.2,
            average_frequency,
            delta=0.003
        )
