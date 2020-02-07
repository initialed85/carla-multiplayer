import datetime
from typing import Optional

import Pyro4

from .controller import ControllerState
from .looper import TimedLooper

try:  # cater for python3 -m (module) vs python3 (file)
    from . import wrapped_carla as carla
except ImportError:
    import wrapped_carla as carla

_CONTROL_RATE = 1.0 / 1.0  # 10 Hz
_CONTROL_EXPIRE = 1.0  # 1 s
_RESET_RATE = 1.0 / 1.0  # 1 Hz

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


@Pyro4.expose
class Vehicle(TimedLooper):
    def __init__(self, client: carla.Client, actor_id: int, control_rate: float = _CONTROL_RATE, control_expire: float = _CONTROL_EXPIRE,
            reset_rate: float = _RESET_RATE):
        super().__init__(
            period=control_rate
        )

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
                self._vehicle.apply_transform(transform)
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

    def _before_loop(self):
        self._vehicle = get_vehicle(self._client, self._actor_id)

    @Pyro4.oneway
    def apply_control(self, controller_state: ControllerState):
        self._controller_state = controller_state
        self._last_controller_state_received = datetime.datetime.now()


if __name__ == '__main__':
    import sys
    import traceback

    _client = carla.Client('localhost', 2000)
    _client.set_timeout(2.0)

    _transform = [x for x in _client.get_world().get_actors() if 'spectator' in x.type_id][0].get_transform()

    _actor_id = create_vehicle(_client, sys.argv[1], _transform)

    _vehicle = Vehicle(_client, _actor_id)

    _DAEMON = Pyro4.Daemon(host=sys.argv[2], port=int(sys.argv[3]))
    _uri = _DAEMON.register(_vehicle, 'vehicle')
    print('listening at {}'.format(repr(_uri)))

    try:
        _DAEMON.requestLoop()
    except Exception as e:
        print('caught {}; traceback follows'.format(repr(e)))
        traceback.print_exc()

    print('shutting down')

    delete_vehicle(_client, _actor_id)
