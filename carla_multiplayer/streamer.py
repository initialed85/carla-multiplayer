import datetime
import socket
import time
from queue import Queue, Empty
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

        self._things: Queue = Queue(maxsize=1024)

    def send(self, thing: Any):
        print('{} - _Client.send - called'.format(datetime.datetime.now()))
        self._things.put(thing)
        print('{} - _Client.send - returning'.format(datetime.datetime.now()))

    def _loop(self):
        while not self._stopped:
            while not self._stopped:
                print('{} - _Client._loop - top'.format(datetime.datetime.now()))

                # timeout = self._socket.gettimeout()
                # try:
                #     self._socket.settimeout(0)
                #     data = self._socket.recv(1024).decode('utf-8')
                #     if 'stop' in data:
                #         print('info: shutdown at remote request')
                #         self._stopped = True
                #         break
                # except socket.error:
                #     pass
                # except Exception as e:
                #     print('error: caught {} trying to read data from socket; closing'.format(repr(e)))
                #     self._stopped = True
                #     break
                # finally:
                #     self._socket.settimeout(timeout)

                try:
                    thing = self._things.get(timeout=1)  # check for something to send
                except IndexError:
                    print('{} - _Client._loop - nothing'.format(datetime.datetime.now()))
                    continue

                try:
                    self._socket.send(thing + _SEPARATOR)  # send the thing
                except Exception as e:
                    print('error: caught {} trying to write data to socket; closing'.format(repr(e)))
                    self._stopped = True
                    break

                print('{} - _Client._loop - bottom'.format(datetime.datetime.now()))

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
        print('{} - Sender.send - called'.format(datetime.datetime.now()))

        with self._client_by_uuid_lock:
            client = self._client_by_uuid.get(uuid)
            if client is None:
                raise ValueError('uuid {} not known'.format(repr(uuid)))

        client.send(thing)

        print('{} - Sender.send - returning'.format(datetime.datetime.now()))

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

    def _loop(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        self._socket.settimeout(5)
        self._socket.connect((self._host, self._port))
        self._socket.settimeout(1)
        self._socket.send('{}\n'.format(str(self._uuid)).encode('utf-8'))

        self._caller = Thread()

        while not self._stopped:
            thing = b''
            while not thing.endswith(_SEPARATOR):
                try:
                    thing += self._socket.recv(1)
                except socket.timeout:
                    continue
                except Exception as e:
                    print('error: caught {} trying to read data from socket; closing socket'.format(repr(e)))
                    self._stopped = True
                    break

            print('{} - Receiver._things._put'.format(datetime.datetime.now()))
            
            self._things.put(thing)

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

    _is_sender = mode.strip().lower()[0] == 's'

    _sender_or_receiver = Sender() if _is_sender else Receiver(_callback, UUID('e66ae528-b01d-435a-8109-2092e04b2532'), 'localhost')

    _sender_or_receiver.start()

    if _is_sender:
        code.interact(local=locals())
    else:
        while 1:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break

    _sender_or_receiver.stop()
