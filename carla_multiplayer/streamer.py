import socket
import time
from collections import deque
from threading import Thread, RLock
from typing import Optional, Tuple, Dict, List, Any, Callable
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

        self._things: deque = deque(maxlen=1024)

    def send(self, thing: Any):
        self._things.append(thing)

    def _loop(self):
        while not self._stopped:
            while not self._stopped:
                timeout = self._socket.gettimeout()
                try:
                    self._socket.settimeout(0)
                    data = self._socket.recv(1024).decode('utf-8')
                    if 'stop' in data:
                        print('info: shutdown at remote request')
                        self._stopped = True
                        break
                except socket.error:
                    pass
                except Exception as e:
                    print('error: caught {} trying to read data from socket; closing'.format(repr(e)))
                    self._stopped = True
                    break
                finally:
                    self._socket.settimeout(timeout)

                try:
                    thing = self._things.popleft()  # check for something to send
                except IndexError:
                    time.sleep(0.1)
                    continue

                try:
                    self._socket.send(thing + _SEPARATOR)  # send the thing
                except Exception as e:
                    print('error: caught {} trying to write data to socket; closing'.format(repr(e)))
                    self._stopped = True
                    break

        self._socket.close()

        self._cleanup_callback(self._uuid)


class Sender(_Looper):
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

    def _loop(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self._socket.bind(('', self._port))
        self._socket.listen(1)

        while not self._stopped:
            try:
                client_socket, client_address = self._socket.accept()
                client_socket.settimeout(1)
            except socket.error:
                time.sleep(0.1)

                continue

            try:
                data = client_socket.recv(1024).decode('utf-8').strip()
            except Exception as e:
                print('error: caught {} trying to read data from client_socket; closing'.format(repr(e)))
                client_socket.close()
                continue

            try:
                uuid = UUID(data)
            except Exception as e:
                print('error: caught {} trying to build uuid from {}; closing'.format(repr(e), repr(data)))
                client_socket.close()
                continue

            if uuid in self._client_by_uuid:
                print('error: uuid {} already exists; closing'.format(repr(uuid)))
                client_socket.close()
                continue

            client = _Client(
                client_socket=client_socket,
                client_address=client_address,
                uuid=uuid,
                cleanup_callback=self._cleanup_callback
            )

            client.start()

            self._client_by_uuid[uuid] = client

        with self._client_by_uuid_lock:
            uuids: List[UUID] = []
            for uuid, client in self._client_by_uuid.items():
                client.stop()
                uuids += [uuid]

        for uuid in uuids:
            self._cleanup_callback(uuid)

        self._socket.close()


class Receiver(_Looper):
    def __init__(self, callback: Callable, uuid: UUID, host: str, port: int = 13338):
        super().__init__()

        self._callback: Callable = callback
        self._uuid: UUID = uuid
        self._host: str = host
        self._port: int = port

        self._socket: Optional[socket.socket] = None

        self._stopped: bool = False

    def _loop(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        self._socket.settimeout(5)
        self._socket.connect((self._host, self._port))
        self._socket.settimeout(1)
        self._socket.send('{}\n'.format(str(self._uuid)).encode('utf-8'))

        while not self._stopped:
            try:
                datas = self._socket.recv(65536).rstrip(_SEPARATOR)
            except socket.timeout:
                time.sleep(0.1)

                continue
            except Exception as e:
                print('error: caught {} trying to read data from socket; closing socket'.format(repr(e)))
                break

            if len(datas) == 0:
                time.sleep(0.1)

                continue

            if not callable(self._callback):
                print('error: {} not callable; closing socket'.format(repr(self._callback)))
                break

            for data in datas.split(_SEPARATOR):
                self._callback(data)

        self._socket.send('stop\n'.encode('utf-8'))
        self._socket.close()


if __name__ == '__main__':
    import sys
    import code


    def _callback(data):
        print(repr(data))


    try:
        mode = sys.argv[1]
    except IndexError:
        raise SystemExit('error: first argument must be "sender" or "receiver"')

    is_sender = mode.strip().lower()[0] == 's'

    thing = Sender() if is_sender else Receiver(_callback, UUID('e66ae528-b01d-435a-8109-2092e04b2532'), 'localhost')

    thing.start()

    if is_sender:
        code.interact(local=locals())
    else:
        while 1:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break

    thing.stop()
