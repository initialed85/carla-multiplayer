from typing import Dict
from uuid import UUID, uuid4

import Pyro4

_START_PORT = 13337

Pyro4.config.SERIALIZERS_ACCEPTED = ['pickle']
Pyro4.config.SERIALIZER = 'pickle'


@Pyro4.expose
class Client(object):
    def __init__(self, uuid: UUID):
        self._uuid: UUID = uuid

    def get_uuid(self) -> UUID:
        return self._uuid


@Pyro4.expose
class Server(object):
    def __init__(self, start_port: int = _START_PORT):
        self._start_port: int = start_port

        self._clients_by_uuid: Dict[UUID, Client] = {}

    def register_client(self):
        uuid = uuid4()
        client = Client(uuid=uuid)
        self._clients_by_uuid[uuid] = client

        return client

    def unregister_client(self, uuid: UUID):
        client = self._clients_by_uuid.pop(uuid, None)
        if client is None:
            raise ValueError('could not find Client for {}'.format(uuid))
