from typing import Optional

import numpy

from . import wrapped_carla as carla

_FPS = 24
_SENSOR_BLUEPRINT_NAME = 'sensor.other.rgb'
_TRANSFORM = carla.Transform(
    carla.Location(-15, 0, 5),
    carla.Rotation(0, 0, 0)
)


def to_bgra_array(image: carla.Image):
    array = numpy.frombuffer(image.raw_data, dtype=numpy.dtype("uint8"))
    array = numpy.reshape(array, (image.height, image.width, 4))

    return array


def to_rgb_array(image: carla.Image):
    array = to_bgra_array(image)
    array = array[:, :, :3]
    array = array[:, :, ::-1]

    return array


class Sensor(object):
    def __init__(self, client: carla.Client, actor_id: int, transform: carla.Transform = _TRANSFORM, fps: int = _FPS,
            sensor_blueprint_name: str = _SENSOR_BLUEPRINT_NAME):
        self._client: carla.Client = client
        self._actor_id: int = actor_id
        self._transform: carla.Transform = transform
        self._fps: float = float(fps)
        self._sensor_blueprint_name = sensor_blueprint_name

        self._world: Optional[carla.World] = None
        self._actor: Optional[carla.Actor] = None
        self._sensor: Optional[carla.Sensor] = None

    def start(self):
        self._world = self._client.get_world()
        self._world.wait_for_tick()

        self._actor = self._world.get_actor(self._actor_id)
        self._world.wait_for_tick()
        if self._actor is None:
            raise ValueError('expected actor to be {} but was {}; likely actor_id {} does not exist'.format(
                carla.Actor,
                type(self._actor),
                self._actor_id
            ))

        blueprint_library = self._world.get_blueprint_library()
        sensor_blueprint = blueprint_library.find(self._sensor_blueprint_name)
        self._sensor = self._world.spawn_actor(
            sensor_blueprint,
            self._transform,
            attach_to=self._actor,
            attachment_type=carla.AttachmentType.SpringArm
        )
        self._world.wait_for_tick()

    def stop(self):
        self._sensor.destroy()
        self._world.wait_for_tick()


if __name__ == '__main__':
    client = carla.Client('localhost', 2000)
    client.set_timeout(2.0)

    sensor = Sensor(client, 1)

    sensor.start()

    sensor.stop()
