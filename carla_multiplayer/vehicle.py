import datetime
import time
from threading import Thread
from typing import Optional, NamedTuple

try:
    from . import wrapped_carla as carla
except ImportError as e:
    raise RuntimeError('got {} stating {}; ensure you run this as a module, not a script (e.g. python -m carla_multiplayer.vehicle)'.format(
        type(e),
        repr(str(e))
    ))

_VEHICLE_BLUEPRINT_NAME = 'vehicle.komatsu.830e'


class Location(NamedTuple):
    x: float
    y: float
    z: float


class Rotation(NamedTuple):
    pitch: float
    yaw: float
    roll: float


class Transform(NamedTuple):
    location: Location
    rotation: Rotation


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

        self._last_reset: Optional[datetime.datetime] = None

        self._stopped: bool = False

    def _expire_control(self):
        while not self._stopped:
            if self._actor is None:
                time.sleep(0.1)

                continue

            if self._last_control_timestamp is not None:
                if datetime.datetime.now() - self._last_control_timestamp < datetime.timedelta(seconds=1):
                    time.sleep(0.1)

                    continue

            self._actor.apply_control(carla.VehicleControl(brake=1.0, hand_brake=True))

    def apply_control(self, throttle: float, steer: float, brake: float, hand_brake: bool, reverse: bool, reset: bool):
        if self._actor is None:
            return

        now = datetime.datetime.now()

        if reset:
            if self._last_reset is None or (now - self._last_reset).total_seconds() > 1:
                actor_transform = self._actor.get_transform()
                actor_transform.location.z += 5
                actor_transform.rotation.roll = 0.0
                actor_transform.rotation.pitch = 0.0
                self._actor.set_transform(actor_transform)

                self._last_reset = now

        vehicle_control = carla.VehicleControl(
            throttle=throttle,
            steer=steer,
            brake=brake,
            hand_brake=hand_brake,
            reverse=reverse,
        )

        self._actor.apply_control(vehicle_control)

        self._last_control_timestamp = now

    def get_actor_id(self) -> int:
        if self._actor is None:
            raise ValueError('actor is None; cannot get id')

        return self._actor.id

    def get_transform(self) -> Transform:
        if self._actor is None:
            raise ValueError('actor is None; cannot get transform')

        carla_transform = self._actor.get_transform()

        return Transform(
            Location(
                carla_transform.location.x,
                carla_transform.location.y,
                carla_transform.location.z
            ),
            Rotation(
                carla_transform.rotation.pitch,
                carla_transform.rotation.yaw,
                carla_transform.rotation.roll
            )
        )

    def start(self):
        self._stopped = False

        self._world = self._client.get_world()
        self._world.wait_for_tick()

        blueprint_library = self._world.get_blueprint_library()
        vehicle_blueprint = blueprint_library.find(self._vehicle_blueprint_name)
        self._actor = self._world.spawn_actor(vehicle_blueprint, self._transform)
        self._world.wait_for_tick()

        self._control_expirer = Thread(target=self._expire_control)
        # self._control_expirer.start()

    def stop(self):
        self._stopped = True

        if self._control_expirer is not None:
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
