import time
import unittest
from typing import List

from .udp import Datagram, Receiver, Sender


class ReceiverAndSenderBase(unittest.TestCase):
    _datagrams = []
    receiver = None
    sender = None

    def _receiver_callback(self, datagram: Datagram):
        self._datagrams += [datagram]

        time.sleep(0.1)

    def tearDown(self) -> None:
        self.receiver.stop()
        self.sender.stop()


class ReceiverAndSenderTest(ReceiverAndSenderBase):
    def setUp(self):
        self._datagrams: List[Datagram] = []

        self.receiver = Receiver(20001, 8, self._receiver_callback)
        self.receiver.start()

        self.sender = Sender(20000, 1024)
        self.sender.start()

    def test_lifecycle(self):
        self.receiver.start()
        self.sender.start()

        for i in range(0, 16):
            self.sender.send_datagram(
                data='Message {} of 16'.format(i + 1).encode('utf-8'),
                address=('', 20001)
            )

        time.sleep(1)

        self.sender.stop()
        self.receiver.stop()

        self.assertEqual([Datagram(data=b'Message 1 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 9 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 10 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 11 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 12 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 13 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 14 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 15 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 16 of 16', address=('127.0.0.1', 20000))],
            self._datagrams
        )


class ReceiverAndSenderSharedSocketTest(ReceiverAndSenderBase):
    def setUp(self):
        self._datagrams: List[Datagram] = []

        self.receiver = Receiver(20000, 8, self._receiver_callback)
        self.receiver.start()

        self.sender = Sender(20000, 1024, socket_override=self.receiver.socket)
        self.sender.start()

    def test_lifecycle(self):
        self.receiver.start()
        self.sender.start()

        for i in range(0, 16):
            self.sender.send_datagram(
                data='Message {} of 16'.format(i + 1).encode('utf-8'),
                address=('', 20000)
            )

        time.sleep(1)

        self.sender.stop()
        self.receiver.stop()

        self.assertEqual([Datagram(data=b'Message 1 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 9 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 10 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 11 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 12 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 13 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 14 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 15 of 16', address=('127.0.0.1', 20000)),
            Datagram(data=b'Message 16 of 16', address=('127.0.0.1', 20000))],
            self._datagrams
        )
