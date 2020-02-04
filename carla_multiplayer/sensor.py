import time
from collections import deque
from io import BytesIO
from threading import Thread
from typing import Optional, Callable

import numpy
from PIL import Image

try:
    from . import wrapped_carla as carla
except ImportError as e:
    raise RuntimeError('got {} stating {}; ensure you run this as a module, not a script (e.g. python -m carla_multiplayer.sensor)'.format(
        type(e),
        repr(str(e))
    ))

_FPS = 24
_WIDTH = 640
_HEIGHT = 360
_SENSOR_BLUEPRINT_NAME = 'sensor.camera.rgb'
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
    def __init__(self,
            client: carla.Client,
            actor_id: int,
            callback: Callable,
            transform: carla.Transform = _TRANSFORM,
            fps: int = _FPS,
            width: int = _WIDTH,
            height: int = _HEIGHT,
            sensor_blueprint_name: str = _SENSOR_BLUEPRINT_NAME):

        self._client: carla.Client = client
        self._actor_id: int = actor_id
        self._callback: Callable = callback
        self._transform: carla.Transform = transform
        self._fps: float = float(fps)
        self._width: int = width
        self._height: int = height
        self._sensor_blueprint_name = sensor_blueprint_name

        self._world: Optional[carla.World] = None
        self._actor: Optional[carla.Actor] = None
        self._sensor: Optional[carla.Sensor] = None

        self._images = deque(maxlen=int(round(self._fps * 10, 0)))
        self._image_handler: Optional[Thread] = None

        self._stopped: bool = False

    def _handle_image_from_deque(self, image: carla.Image):
        rgb_array = to_rgb_array(image)
        pil_image = Image.fromarray(rgb_array)
        buffer = BytesIO()
        pil_image.save(buffer, format='jpeg')
        data = buffer.getvalue()

        self._callback(
            carla_image=image,
            pil_image=pil_image,
            data=data,
        )

    def _handle_images_from_deque(self):
        while not self._stopped:
            try:
                image: carla.Image = self._images.popleft()
            except IndexError:
                time.sleep(0.01)

                continue

            self._handle_image_from_deque(image)

    def _handle_image_from_sensor(self, image: carla.Image):
        self._images.append(image)

    def start(self):
        self._stopped = False

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
        sensor_blueprint.set_attribute('sensor_tick', str(1.0 / self._fps))
        sensor_blueprint.set_attribute('image_size_x', str(self._width))
        sensor_blueprint.set_attribute('image_size_y', str(self._height))
        self._sensor = self._world.spawn_actor(
            sensor_blueprint,
            self._transform,
            attach_to=self._actor,
            attachment_type=carla.AttachmentType.SpringArm
        )
        self._world.wait_for_tick()

        self._image_handler = Thread(target=self._handle_images_from_deque)
        self._image_handler.start()

        self._sensor.listen(self._handle_image_from_sensor)
        self._world.wait_for_tick()

    def stop(self):
        self._stopped = True

        if self._image_handler is not None:
            try:
                self._image_handler.join()
            except RuntimeError:
                pass

        if self._sensor is not None:
            self._sensor.destroy()
            self._sensor = None
            self._world.wait_for_tick()


if __name__ == '__main__':
    def callback(carla_image, pil_image, data):
        print(carla_image, pil_image, data[0:64])


    _client = carla.Client('localhost', 2000)
    _client.set_timeout(2.0)

    _actor_id = [x.id for x in _client.get_world().get_actors() if 'spectator' in x.type_id or 'vehicle' in x.type_id][-1]

    _sensor = Sensor(_client, _actor_id, callback)
    _sensor.start()

    print('ctrl + c to exit')
    while 1:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    _sensor.stop()
