import datetime
import time
from threading import Thread
from typing import Optional

try:
    from . import wrapped_carla as carla
except ImportError as e:
    raise RuntimeError('got {} stating {}; ensure you run this as a module, not a script (e.g. python -m carla_multiplayer.vehicle)'.format(
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

        self._last_control_timestamp: Optional[datetime.datetime] = None
        self._control_expirer: Optional[Thread] = None

        self._stopped: bool = False

    def _expire_control(self):
        while not self._stopped:
            if self._actor is None:
                time.sleep(0.01)

                continue

            if self._last_control_timestamp is not None:
                if datetime.datetime.now() - self._last_control_timestamp < datetime.timedelta(seconds=1):
                    time.sleep(0.01)

                    continue

            self._actor.apply_control(carla.VehicleControl(brake=1.0, hand_brake=True))

    def apply_control(self, throttle: float, steer: float, brake: float, hand_brake: bool, reverse: bool):
        if self._actor is None:
            return

        self._actor.apply_control(carla.VehicleControl(
            throttle=throttle,
            steer=steer,
            brake=brake,
            hand_brake=hand_brake,
            reverse=reverse
        ))

    def get_actor_id(self) -> int:
        if self._actor is None:
            raise ValueError('actor is None; cannot get id')

        return self._actor.id

    def start(self):
        self._stopped = False

        self._world = self._client.get_world()
        self._world.wait_for_tick()

        blueprint_library = self._world.get_blueprint_library()
        vehicle_blueprint = blueprint_library.find(self._vehicle_blueprint_name)
        self._actor = self._world.spawn_actor(vehicle_blueprint, self._transform)
        self._world.wait_for_tick()

        self._control_expirer = Thread(target=self._expire_control)
        self._control_expirer.start()

    def stop(self):
        self._stopped = True

        try:
            self._control_expirer.join()
        except RuntimeError:
            pass

        if self._actor is not None:
            self._actor.destroy()
            self._actor = None
            self._world.wait_for_tick()


if __name__ == '__main__':
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
