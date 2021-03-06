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
    _use_socket_from: Optional['_SocketMixIn']  # because this type isn't defined yet
    socket: socket.socket

    def _before_start(self):
        if self._use_socket_from is not None:
            self._socket = self._use_socket_from.socket
        else:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self._socket.settimeout(1)
        try:
            self._socket.bind(('', self._port))
        except OSError:  # likely _use_shared_socket is True and socket is already bound
            pass

    def _after_stop(self):
        self._socket = None


class Receiver(_SocketMixIn, Threader):
    def __init__(self, port: int, queue_size: int, callback: Optional[Callable] = None, use_socket_from: Optional[_SocketMixIn] = None):
        super().__init__()

        self._port: int = port
        self._queue_size: int = queue_size
        self._callback: Optional[Callable] = None
        self._use_socket_from: Optional[_SocketMixIn] = use_socket_from

        self._socket: Optional[socket.socket] = None
        self._datagrams: Queue = Queue(maxsize=self._queue_size)

        if callback is not None:
            self.set_callback(callback)

    @property
    def socket(self):
        return self._socket

    def set_callback(self, callback: Callable):
        if not callable(callback):
            raise TypeError('expected callback to be callable, but instead was {} of type {}'.format(
                repr(callback),
                type(callback)
            ))

        self._callback = callback

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

            if self._callback is None:
                print('warning: received datagram but callback is None; throwing away')
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
    def __init__(self, port: int, queue_size: int, use_socket_from: Optional[_SocketMixIn] = None):
        super().__init__()

        self._port: int = port
        self._queue_size: int = queue_size
        self._use_socket_from: Optional[_SocketMixIn] = use_socket_from

        self._socket: Optional[socket.socket] = None
        self._datagrams: Queue = Queue(maxsize=self._queue_size)

    @property
    def socket(self):
        return self._socket

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

    def send_datagram(self, data, address):
        self._datagrams.put_nowait(
            Datagram(
                data=data,
                address=address
            )
        )
