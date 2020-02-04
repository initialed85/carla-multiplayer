from typing import Optional

try:
    from . import wrapped_carla as carla
except ImportError as e:
    raise RuntimeError('got {} stating {}; ensure you run this as a module, not a script (e.g. python -m carla_multiplayer.sensor)'.format(
        type(e),
        repr(str(e))
    ))

_VEHICLE_BLUEPRINT_NAME = 'vehicle.komatsu.830e'


def _get_transform(x: float = 0.0, y: float = 0.0, z: float = 0.0, pitch: float = 0.0, yaw: float = 0.0, roll: float = 0.0):
    return carla.Transform(
        carla.Location(x, y, z),
        carla.Rotation(pitch, yaw, roll)
    )


class Vehicle(object):
    def __init__(self,
            client: carla.Client,
            transform: carla.Transform,
            vehicle_blueprint_name: str = _VEHICLE_BLUEPRINT_NAME):
        self._client: carla.Client = client
        self._transform: carla.Transform = transform
        self._vehicle_blueprint_name = vehicle_blueprint_name

        self._world: Optional[carla.World] = None
        self._actor: Optional[carla.Actor] = None

        self._stopped = False

    def start(self):
        self._stopped = False

        self._world = self._client.get_world()
        self._world.wait_for_tick()

        blueprint_library = self._world.get_blueprint_library()
        vehicle_blueprint = blueprint_library.find(self._vehicle_blueprint_name)
        self._actor = self._world.spawn_actor(vehicle_blueprint, self._transform)
        self._world.wait_for_tick()

    def stop(self):
        self._stopped = True

        if self._actor is not None:
            self._actor.destroy()
            self._world.wait_for_tick()


if __name__ == '__main__':
    import time

    _client = carla.Client('localhost', 2000)
    _client.set_timeout(2.0)

    _transform = [x for x in _client.get_world().get_actors() if 'spectator' in x.type_id][0].get_transform()

    _vehicle = Vehicle(_client, _transform)
    _vehicle.start()

    print('ctrl + c to exit')
    while 1:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    _vehicle.stop()
