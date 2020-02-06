import socket
import time
from threading import Thread
from typing import List
from uuid import UUID

from .streamer import _Client, _Sender, _Receiver

_SEPARATOR = b'__what_are_the_chances_these_characters_occur_naturally__'


class TCPSender(_Sender):
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


class TCPReceiver(_Receiver):
    def _loop(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        self._socket.settimeout(5)
        self._socket.connect((self._host, self._port))
        self._socket.settimeout(1)
        self._socket.send('{}\n'.format(str(self._uuid)).encode('utf-8'))

        self._caller = Thread(target=self._call)
        self._caller.start()

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

            self._things.put(thing)

        self._socket.close()

        self._caller.join()


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

    _sender_or_receiver = TCPSender() if _is_sender else TCPReceiver(_callback, UUID('e66ae528-b01d-435a-8109-2092e04b2532'), 'localhost')

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
