import socket
from queue import Queue, Empty
from threading import RLock
from threading import Thread
from typing import Dict
from typing import Optional
from typing import Tuple, Any, Callable
from uuid import UUID

_SEPARATOR = b'__what_are_the_chances_these_characters_occur_naturally__'


class _Looper(object):
    def __init__(self):
        self._looper: Optional[Thread] = None
        self._stopped: bool = False

    def start(self):
        self._stopped = False

        self._looper = Thread(target=self._loop)
        self._looper.start()

    def _loop(self):
        raise NotImplementedError('the _loop method should be overridden')

    def stop(self):
        self._stopped = True

        if self._looper is not None:
            self._looper.join()
            self._looper = None


class _Client(_Looper):
    def __init__(self, client_socket: socket.socket, client_address: Tuple[str, int], uuid: UUID, cleanup_callback: Callable):
        super().__init__()

        self._socket: socket.socket = client_socket
        self._address: Tuple[str, int] = client_address
        self._uuid: uuid = uuid
        self._cleanup_callback: Callable = cleanup_callback

        self._things: Queue = Queue(maxsize=1024)

    def send(self, thing: Any):
        self._things.put(thing)

    def _loop(self):
        while not self._stopped:
            while not self._stopped:
                try:
                    thing = self._things.get(timeout=1)  # check for something to send
                except Empty:
                    continue

                try:
                    # self._socket.send(thing + _SEPARATOR)  # send the thing
                    self._socket.sendto(thing + _SEPARATOR, self._address)  # send the thing
                except Exception as e:
                    print('error: caught {} trying to write data to socket; closing'.format(repr(e)))
                    self._stopped = True
                    break

        self._socket.close()

        self._cleanup_callback(self._uuid)


class _Sender(_Looper):
    def __init__(self, port: int = 13338):
        super().__init__()

        self._port: int = port

        self._socket: Optional[socket.socket] = None
        self._client_by_uuid_lock: RLock = RLock()
        self._client_by_uuid: Dict[UUID, _Client] = {}

    def _cleanup_callback(self, uuid: UUID):
        with self._client_by_uuid_lock:
            self._client_by_uuid.pop(uuid)

    def send(self, uuid: UUID, thing: Any):
        with self._client_by_uuid_lock:
            client = self._client_by_uuid.get(uuid)
            if client is None:
                raise ValueError('uuid {} not known'.format(repr(uuid)))

        client.send(thing)


class _Receiver(_Looper):
    def __init__(self, callback: Callable, uuid: UUID, host: str, port: int = 13338):
        super().__init__()

        self._callback: Callable = callback
        self._uuid: UUID = uuid
        self._host: str = host
        self._port: int = port

        self._socket: Optional[socket.socket] = None
        self._things: Queue = Queue(maxsize=1024)
        self._caller: Optional[Thread] = None

        self._stopped: bool = False

    def _call(self):
        while not self._stopped:
            try:
                thing = self._things.get(timeout=1)
            except Empty:
                continue

            if not callable(self._callback):
                print('error: {} not callable; closing socket'.format(repr(self._callback)))
                return

            self._callback(_SEPARATOR.join(thing.split(_SEPARATOR)[0:-1]))
