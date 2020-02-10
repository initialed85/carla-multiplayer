import time
from typing import Optional, List

from .sensor import create_sensor, _SENSOR_BLUEPRINT_NAME, _SENSOR_TRANSFORM, _FPS, _WIDTH, _HEIGHT, Sensor, delete_sensor
from .udp import Receiver, Sender
from .vehicle import create_vehicle, Vehicle, delete_vehicle

try:  # cater for python3 -m (module) vs python3 (file)
    from . import wrapped_carla as carla
except ImportError:
    import wrapped_carla as carla

_CARLA_HOST = 'localhost'
_CARLA_PORT = 2000
_CARLA_TIMEOUT = 2.0
_QUEUE_DEPTH = 2


class Server(object):
    def __init__(self,
            vehicle_port: int,
            sensor_port: int,
            vehicle_blueprint_name: str,
            client_host: str,
            vehicle_transforms: Optional[List[carla.Transform]] = None,
            sensor_blueprint_name: str = _SENSOR_BLUEPRINT_NAME,
            sensor_transform: carla.Transform = _SENSOR_TRANSFORM,
            carla_host: str = _CARLA_HOST,
            carla_port: int = _CARLA_PORT,
            carla_timeout: int = _CARLA_TIMEOUT,
            queue_depth: int = _QUEUE_DEPTH):
        self._vehicle_blueprint_name: str = vehicle_blueprint_name
        self._vehicle_port: int = vehicle_port
        self._sensor_port: int = sensor_port
        self._client_host: str = client_host
        self._vehicle_transforms: Optional[List[carla.Transform]] = vehicle_transforms
        self._sensor_blueprint_name: str = sensor_blueprint_name
        self._sensor_transform: carla.Transform = sensor_transform
        self._carla_host: str = carla_host
        self._carla_port: int = carla_port
        self._carla_timeout: float = carla_timeout
        self._queue_depth: int = queue_depth

        self._vehicle_actor: carla.Actor = None
        self._sensor_actor: carla.Actor = None

        self._receiver: Receiver = Receiver(self._vehicle_port, self._queue_depth, use_shared_socket=True)
        self._vehicle: Optional[Vehicle] = None

        self._sender: Sender = Sender(self._sensor_port, self._queue_depth, use_shared_socket=True)
        self._sensor: Optional[Sensor] = None

        self._client: carla.Client = carla.Client(self._carla_host, self._carla_port)
        self._client.set_timeout(self._carla_timeout)

        self._stopped = False

    def start(self):
        self._stopped = False

        world = self._client.get_world()
        if world is None:
            raise ValueError('attempt to get world returned None; carla.Client possibly not working')

        if self._vehicle_transforms is None:
            self._vehicle_transforms = [x.get_transform() for x in world.get_actors() if x.type_id == 'spectator']

        while not self._stopped:
            if self._vehicle_actor is not None:
                break

            for transform in self._vehicle_transforms:
                try:
                    self._vehicle_actor = create_vehicle(self._client, self._vehicle_blueprint_name, transform)
                    break
                except RuntimeError:
                    continue

        if self._stopped:
            return

        self._sensor_actor = create_sensor(
            self._client,
            self._vehicle_actor.id,
            self._sensor_blueprint_name,
            _FPS,
            _WIDTH,
            _HEIGHT,
            self._sensor_transform
        )

        if self._stopped:
            return

        self._vehicle = Vehicle(self._receiver, self._client, self._vehicle_actor.id)
        self._sensor = Sensor(self._client, self._sensor_actor.id, self._queue_depth, self._sender, self._client_host, self._sensor_port)

        self._receiver.set_callback(self._vehicle.recv)

        self._receiver.start()
        self._vehicle.start()

        self._sender.start()
        self._sensor.start()

    def run(self):
        if self._stopped:
            return

        while not self._stopped:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break

    def stop(self):
        if self._stopped:
            return

        self._sensor.stop()
        self._sender.stop()
        delete_sensor(self._client, self._sensor_actor.id)

        self._vehicle.stop()
        self._receiver.stop()
        delete_vehicle(self._client, self._vehicle_actor.id)


def run_server(port: int,
        vehicle_blueprint_name: str,
        client_host: str,
        vehicle_transforms: Optional[List[carla.Transform]] = None,
        sensor_blueprint_name: str = _SENSOR_BLUEPRINT_NAME,
        sensor_transform: carla.Transform = _SENSOR_TRANSFORM,
        carla_host: str = _CARLA_HOST,
        carla_port: int = _CARLA_PORT,
        carla_timeout: int = _CARLA_TIMEOUT,
        queue_depth: int = _QUEUE_DEPTH):
    server = Server(
        vehicle_port=port,
        sensor_port=port,
        vehicle_blueprint_name=vehicle_blueprint_name,
        client_host=client_host,
        vehicle_transforms=vehicle_transforms,
        sensor_blueprint_name=sensor_blueprint_name,
        sensor_transform=sensor_transform,
        carla_host=carla_host,
        carla_port=carla_port,
        carla_timeout=carla_timeout,
        queue_depth=queue_depth
    )

    server.start()
    server.run()
    server.stop()


if __name__ == '__main__':
    import sys

    run_server(int(sys.argv[1]), sys.argv[2], sys.argv[3])
