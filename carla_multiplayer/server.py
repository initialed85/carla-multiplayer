import time
from typing import Optional, List

from .sensor import create_sensor, _SENSOR_BLUEPRINT_NAME, _SENSOR_TRANSFORM, _FPS, _WIDTH, _HEIGHT, Sensor, delete_sensor
from .udp import Receiver, Sender
from .vehicle import create_vehicle, Vehicle, delete_vehicle, _CONTROL_RATE, _CONTROL_EXPIRE, _RESET_RATE

try:  # cater for python3 -m (module) vs python3 (file)
    from . import wrapped_carla as carla
except ImportError:
    import wrapped_carla as carla

_CARLA_PORT = 2000
_CARLA_TIMEOUT = 2.0
_QUEUE_SIZE = 2


class Server(object):
    def __init__(self,
            vehicle_port: int,
            sensor_port: int,
            vehicle_blueprint_name: str,
            client_host: str,
            carla_host: str,
            vehicle_transforms: Optional[List[carla.Transform]] = None,
            sensor_blueprint_name: str = _SENSOR_BLUEPRINT_NAME,
            sensor_transform: carla.Transform = _SENSOR_TRANSFORM,
            carla_port: int = _CARLA_PORT,
            carla_timeout: int = _CARLA_TIMEOUT,
            queue_size: int = _QUEUE_SIZE,
            control_rate: float = _CONTROL_RATE,
            control_expire: float = _CONTROL_EXPIRE,
            reset_rate: float = _RESET_RATE,
            fps: int = _FPS,
            width: int = _WIDTH,
            height: int = _HEIGHT):
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
        self._queue_size: int = queue_size
        self._control_rate: float = control_rate
        self._control_expire: float = control_expire
        self._reset_rate: float = reset_rate
        self._fps: int = fps
        self._width: int = width
        self._height: int = height

        self._vehicle_actor: carla.Actor = None
        self._sensor_actor: carla.Actor = None

        self._receiver: Receiver = Receiver(
            port=self._vehicle_port,
            queue_size=self._queue_size,
        )
        self._vehicle: Optional[Vehicle] = None

        self._sender: Sender = Sender(
            port=self._sensor_port,
            queue_size=self._queue_size,
            use_socket_from=self._receiver
        )
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
            client=self._client,
            actor_id=self._vehicle_actor.id,
            sensor_blueprint_name=self._sensor_blueprint_name,
            fps=self._fps,
            width=self._width,
            height=self._height,
            transform=self._sensor_transform
        )

        if self._stopped:
            return

        self._vehicle = Vehicle(
            receiver=self._receiver,
            client=self._client,
            actor_id=self._vehicle_actor.id,
            control_rate=self._control_rate,
            control_expire=self._control_expire,
            reset_rate=self._reset_rate
        )

        self._sensor = Sensor(
            client=self._client,
            actor_id=self._sensor_actor.id,
            queue_size=self._queue_size,
            sender=self._sender,
            host=self._client_host,
            port=self._sensor_port
        )

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
        carla_host: str,
        vehicle_transforms: Optional[List[carla.Transform]] = None,
        sensor_blueprint_name: str = _SENSOR_BLUEPRINT_NAME,
        sensor_transform: carla.Transform = _SENSOR_TRANSFORM,
        carla_port: int = _CARLA_PORT,
        carla_timeout: int = _CARLA_TIMEOUT,
        queue_size: int = _QUEUE_SIZE,
        control_rate: float = _CONTROL_RATE,
        control_expire: float = _CONTROL_EXPIRE,
        reset_rate: float = _RESET_RATE,
        fps: int = _FPS,
        width: int = _WIDTH,
        height: int = _HEIGHT):
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
        queue_size=queue_size,
        control_rate=control_rate,
        control_expire=control_expire,
        reset_rate=reset_rate,
        fps=fps,
        width=width,
        height=height
    )

    server.start()
    server.run()
    server.stop()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--vehicle-blueprint-name', type=str, required=True)
    parser.add_argument('--client-host', type=str, required=True)
    parser.add_argument('--carla-host', type=str, required=True)
    parser.add_argument('--sensor-blueprint_name', type=str, default=_SENSOR_BLUEPRINT_NAME)
    parser.add_argument('--carla-port', type=int, default=_CARLA_PORT)
    parser.add_argument('--carla-timeout', type=float, default=_CARLA_TIMEOUT)
    parser.add_argument('--queue-size', type=int, default=_QUEUE_SIZE)
    parser.add_argument('--control-rate', type=float, default=_CONTROL_RATE)
    parser.add_argument('--control-expire', type=float, default=_CONTROL_EXPIRE)
    parser.add_argument('--reset-rate', type=float, default=_RESET_RATE)
    parser.add_argument('--fps', type=int, default=_FPS)
    parser.add_argument('--width', type=int, default=_WIDTH)
    parser.add_argument('--height', type=int, default=_HEIGHT)

    args = parser.parse_args()

    run_server(
        port=args.port,
        vehicle_blueprint_name=args.vehicle_blueprint_name,
        client_host=args.client_host,
        sensor_blueprint_name=args.sensor_blueprint_name,
        carla_host=args.carla_host,
        carla_port=args.carla_port,
        carla_timeout=args.carla_timeout,
        queue_size=args.queue_size,
        control_rate=args.control_rate,
        control_expire=args.control_expire,
        reset_rate=args.reset_rate,
        fps=args.fps,
        width=args.width,
        height=args.height
    )
