import datetime
from typing import Optional

import Pyro4

from .controller import ControllerState, deserialize_controller_state
from .looper import TimedLooper
from .udp import Receiver, Datagram

try:  # cater for python3 -m (module) vs python3 (file)
    from . import wrapped_carla as carla
except ImportError:
    import wrapped_carla as carla

Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.SERIALIZERS_ACCEPTED = ['pickle']

_CONTROL_RATE = 1.0 / 10.0  # 10 Hz
_CONTROL_EXPIRE = 1.0  # 1 s
_RESET_RATE = 1.0 / 1.0  # 1 Hz
_CARLA_PORT = 2000
_CARLA_TIMEOUT = 2.0
_QUEUE_SIZE = 2

_SAFE_CONTROL = carla.VehicleControl(throttle=0.0, brake=1.0, hand_brake=True)


def create_vehicle(
        client: carla.Client,
        vehicle_blueprint_name: str,
        transform: carla.Transform) -> carla.Actor:
    world = client.get_world()
    world.wait_for_tick()

    blueprint_library = world.get_blueprint_library()
    vehicle_blueprint = blueprint_library.find(vehicle_blueprint_name)
    vehicle = world.spawn_actor(
        vehicle_blueprint,
        transform,
    )
    world.wait_for_tick()

    return vehicle


def get_vehicle(client: carla.Client, actor_id: int) -> carla.Actor:
    world = client.get_world()
    world.wait_for_tick()

    vehicle = world.get_actor(actor_id)
    world.wait_for_tick()

    if vehicle is None:
        raise ValueError('failed to get vehicle for actor_id {}; valid options right now are {}'.format(
            actor_id,
            {x.id: x.type_id for x in world.get_actors().filter('vehicle.*')}
        ))

    return vehicle


def delete_vehicle(client: carla.Client, actor_id: int):
    get_vehicle(client, actor_id).destroy()
    client.get_world().wait_for_tick()


class Vehicle(TimedLooper):
    def __init__(self,
            receiver: Receiver,
            client: carla.Client,
            actor_id: int,
            control_rate: float = _CONTROL_RATE,
            control_expire: float = _CONTROL_EXPIRE,
            reset_rate: float = _RESET_RATE):
        super().__init__(
            period=control_rate
        )

        self._receiver: Receiver = receiver
        self._client: carla.Client = client
        self._actor_id: int = actor_id
        self._control_rate: float = control_rate
        self._control_expire: float = control_expire
        self._reset_rate: float = reset_rate

        self._control_expire_delta = datetime.timedelta(seconds=self._control_expire)
        self._last_controller_state_received: Optional[datetime.datetime] = None
        self._controller_state: Optional[ControllerState] = None
        self._reset_rate_delta = datetime.timedelta(seconds=self._reset_rate)
        self._last_reset: Optional[datetime.datetime] = None

        self._vehicle: Optional[carla.Actor] = None

    def _before_loop(self):
        self._vehicle = get_vehicle(self._client, self._actor_id)

    def _work(self):
        now = datetime.datetime.now()

        if self._last_controller_state_received is not None:
            if now - self._last_controller_state_received > self._control_expire_delta:
                self._vehicle.apply_control(_SAFE_CONTROL)
                return

        if self._controller_state is None:
            return

        if self._controller_state.reset:
            if self._last_reset is None or now - self._last_reset > self._reset_rate_delta:
                transform = self._vehicle.get_transform()
                transform.location.z += 5
                transform.rotation.roll = 0
                transform.rotation.pitch = 0
                self._vehicle.set_transform(transform)
                self._last_reset = now

        self._vehicle.apply_control(
            carla.VehicleControl(
                throttle=self._controller_state.throttle,
                brake=self._controller_state.brake,
                steer=self._controller_state.steer,
                hand_brake=self._controller_state.hand_brake,
                reverse=self._controller_state.reverse
            )
        )

    def _apply_control(self, controller_state: ControllerState):
        if controller_state is None:
            return

        self._controller_state = controller_state
        self._last_controller_state_received = datetime.datetime.now()

    def recv(self, datagram: Datagram):
        controller_state = deserialize_controller_state(datagram.data)

        self._apply_control(controller_state)


if __name__ == '__main__':
    import argparse
    import time

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--vehicle-blueprint-name', type=str, required=True)
    parser.add_argument('--carla-host', type=str, required=True)
    parser.add_argument('--carla-port', type=int, default=_CARLA_PORT)
    parser.add_argument('--carla-timeout', type=float, default=_CARLA_TIMEOUT)

    args = parser.parse_args()

    _receiver = Receiver(args.port, args.queue_size)
    _receiver.start()

    _client = carla.Client('localhost', 2000)
    _client.set_timeout(2.0)

    _transform = [x for x in _client.get_world().get_actors() if 'spectator' in x.type_id][0].get_transform()

    _actor_id = create_vehicle(_client, sys.argv[2], _transform).id

    _vehicle = Vehicle(_receiver, _client, _actor_id)
    _vehicle.start()

    _receiver.set_callback(_vehicle.recv)

    while 1:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    _vehicle.stop()
    delete_vehicle(_client, _actor_id)

    _receiver.stop()
