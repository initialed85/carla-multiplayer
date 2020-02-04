import time
from itertools import cycle
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from .sensor import Sensor
from .vehicle import Vehicle

try:
    from . import wrapped_carla as carla
except ImportError as e:
    raise RuntimeError(
        'got {} stating {}; ensure you run this as a module, not a script (e.g. python -m carla_multiplayer.server)'.format(
            type(e),
            repr(str(e))
        ))


class Player(object):
    def __init__(self, client: carla.Client, uuid: UUID, transforms: List[carla.Transform]):
        self._client: carla.Client = client
        self._uuid: UUID = uuid
        self._transforms: carla.Transform = transforms

        self._vehicle: Optional[Vehicle] = None
        self._sensor: Optional[Sensor] = None

    def start(self):
        for transform in cycle(self._transforms):
            self._vehicle = Vehicle(self._client, transform)

            try:
                self._vehicle.start()

                break
            except Exception as e:
                print('failed to spawn because {}; trying again'.format(repr(e)))

                self._vehicle.stop()

                time.sleep(1)

    def stop(self):
        self._vehicle.stop()


class Server(object):
    def __init__(self, client: carla.Client, transforms: List[carla.Transform]):
        self._client: carla.Client = client
        self._transforms: List[carla.Transform] = transforms

        self._players_by_uuid: Dict[UUID, Player] = {}

        self._stopped: bool = False

    def start(self):
        self._stopped = False

    def register_player(self):
        uuid = uuid4()

        player = Player(
            client=self._client,
            uuid=uuid,
            transforms=self._transforms
        )

        player.start()

        self._players_by_uuid[uuid] = player

        return uuid

    def unregister_player(self, uuid: UUID):
        player = self._players_by_uuid.pop(uuid)
        if player is None:
            raise ValueError('no player for {}'.format(repr(uuid)))

        player.stop()

    def stop(self):
        self._stopped = False


if __name__ == '__main__':
    import code

    _client = carla.Client('localhost', 2000)
    _client.set_timeout(2.0)

    _transforms = [[x for x in _client.get_world().get_actors() if 'spectator' in x.type_id][0].get_transform()]

    _server = Server(_client, _transforms)
    _server.start()

    code.interact(local=locals())

    _server.stop()
