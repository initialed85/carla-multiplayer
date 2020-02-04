import time
from itertools import cycle
from typing import Dict, List, Optional
from uuid import uuid4, UUID

import Pyro4
from PIL import Image

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

Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.SERIALIZERS_ACCEPTED = ['pickle']
Pyro4.config.COMPRESSION = True


@Pyro4.expose
class Player(object):
    def __init__(self, client: carla.Client, uuid: UUID, transforms: List[carla.Transform]):
        self._client: carla.Client = client
        self._uuid: UUID = uuid
        self._transforms: carla.Transform = transforms

        self._vehicle: Optional[Vehicle] = None
        self._sensor: Optional[Sensor] = None

        self._frame: Optional[bytes] = None

    @property
    def uuid(self):
        return self._uuid

    def _callback(self, carla_image: carla.Image, pil_image: Image.Image, data: bytes):
        _ = carla_image
        _ = pil_image

        self._frame = data

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

        self._sensor = Sensor(self._client, self._vehicle.get_actor_id(), self._callback)

        self._sensor.start()

    def get_frame(self) -> Optional[bytes]:
        return self._frame

    def get_transform(self):
        return self._vehicle.get_transform()

    @Pyro4.oneway
    def apply_control(self, throttle: float, steer: float, brake: float, hand_brake: bool, reverse: bool):
        if self._vehicle is None:
            return

        self._vehicle.apply_control(
            throttle=throttle,
            steer=steer,
            brake=brake,
            hand_brake=hand_brake,
            reverse=reverse
        )

    def stop(self):
        self._sensor.stop()
        self._vehicle.stop()


@Pyro4.expose
class Server(object):
    def __init__(self, client: carla.Client, transforms: List[carla.Transform]):
        self._client: carla.Client = client
        self._transforms: List[carla.Transform] = transforms

        self._players_by_uuid: Dict[UUID, Player] = {}

        self._stopped: bool = False

    def start(self):
        self._stopped = False

    def register_player(self) -> UUID:
        uuid = uuid4()

        player = Player(
            client=self._client,
            uuid=uuid,
            transforms=self._transforms
        )

        player.start()

        self._players_by_uuid[uuid] = player

        return uuid

    def get_player(self, uuid: UUID) -> Player:
        player = self._players_by_uuid.get(uuid)
        if player is None:
            raise ValueError('no player for {}'.format(repr(uuid)))

        return player

    def get_proxy_player(self, uuid: UUID) -> Player:
        global _DAEMON

        player = self.get_player(uuid)

        _DAEMON.register(player)

        return player

    def get_players(self) -> List[Player]:
        return list(self._players_by_uuid.values())

    def unregister_player(self, uuid: UUID):
        player = self._players_by_uuid.pop(uuid, None)
        if player is None:
            raise ValueError('no player for {}'.format(repr(uuid)))

        player.stop()

    def stop(self):
        self._stopped = True

        for player in self.get_players():
            self.unregister_player(player.uuid)


if __name__ == '__main__':
    import traceback
    import sys

    try:
        _host = sys.argv[1]
    except Exception:
        raise SystemExit('error: first argument must be address of interface to listen on')

    _client = carla.Client('localhost', 2000)
    _client.set_timeout(2.0)

    _transforms = [[x for x in _client.get_world().get_actors() if 'spectator' in x.type_id][0].get_transform()]

    _server = Server(_client, _transforms)
    _server.start()

    _DAEMON = Pyro4.Daemon(host=_host, port=13337)

    _uri = _DAEMON.register(_server, 'carla_multiplayer')
    print('listening at {}'.format(repr(_uri)))

    try:
        _DAEMON.requestLoop()
    except Exception as e:
        print('caught {}; traceback follows'.format(repr(e)))
        traceback.print_exc()

    print('shutting down')

    _server.stop()
