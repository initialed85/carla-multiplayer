import socket
import traceback
from queue import Queue, Full, Empty
from threading import Thread
from typing import Optional, NamedTuple, Tuple, Callable

from .threader import Threader

_MAX_UDP_DATAGRAM = 65507  # https://en.wikipedia.org/wiki/User_Datagram_Protocol#UDP_datagram_structure


class Datagram(NamedTuple):
    data: bytes
    address: Tuple[str, int]


class _SocketMixIn(object):
    _socket: Optional[socket.socket]
    _port: int

    def _before_start(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(1)
        self._socket.bind(('', self._port))

    def _after_stop(self):
        self._socket = None


class Receiver(_SocketMixIn, Threader):
    def __init__(self, port: int, max_queue_size: int, callback: Callable):
        super().__init__()

        self._port: int = port
        self._max_queue_size: int = max_queue_size
        self._callback: Callable = callback

        self._socket: Optional[socket.socket] = None
        self._datagrams: Queue = Queue(maxsize=self._max_queue_size)

    def _fill_datagram_queue_from_socket(self):
        while not self._stop_event.is_set():
            try:
                data, address = self._socket.recvfrom(_MAX_UDP_DATAGRAM)

            except socket.timeout:
                continue
            except Exception as e:
                print('attempt to receive from {} in {} raised {}; traceback follows'.format(
                    repr(self._socket),
                    repr(self),
                    repr(e)
                ))
                traceback.print_exc()
                continue

            datagram = Datagram(
                data=data,
                address=address
            )

            while not self._stop_event.is_set():
                try:
                    self._datagrams.put_nowait(datagram)
                    break
                except Full:  # attempt to remove the oldest datagram
                    try:
                        self._datagrams.get_nowait()
                    except Empty:
                        pass

    def _drain_datagram_queue_to_callbacks(self):
        while not self._stop_event.is_set():
            try:
                datagram = self._datagrams.get(timeout=1)
            except Empty:
                continue

            try:
                self._callback(datagram)
            except Exception as e:
                print('attempt to call {} in {} raised {}; traceback follows'.format(
                    repr(self._callback),
                    repr(self),
                    repr(e)
                ))
                traceback.print_exc()
                continue

    def _create_threads(self):
        self._threads = [
            Thread(target=self._drain_datagram_queue_to_callbacks),
            Thread(target=self._fill_datagram_queue_from_socket),
        ]


class Sender(_SocketMixIn, Threader):
    def __init__(self, port: int, max_queue_size: int):
        super().__init__()

        self._port: int = port
        self._max_queue_size: int = max_queue_size

        self._socket: Optional[socket.socket] = None
        self._datagrams: Queue = Queue(maxsize=self._max_queue_size)

    def _drain_datagram_queue_to_socket(self):
        while not self._stop_event.is_set():
            try:
                datagram = self._datagrams.get(timeout=1)
            except Empty:
                continue

            try:
                self._socket.sendto(datagram.data, datagram.address)
            except socket.error:
                continue
            except Exception as e:
                print('attempt to send {} bytes to {} in {} raised {}; traceback follows'.format(
                    len(datagram.data),
                    repr(datagram.address),
                    repr(self),
                    repr(e)
                ))
                traceback.print_exc()
                continue

    def _create_threads(self):
        self._threads = [
            Thread(target=self._drain_datagram_queue_to_socket),
        ]

    def _before_start(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(1)
        self._socket.bind(('', self._port))

    def _after_stop(self):
        self._socket = None

    def send_datagram(self, data, address):
        self._datagrams.put_nowait(
            Datagram(
                data=data,
                address=address
            )
        )
