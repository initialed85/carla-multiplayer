import numpy

try:  # cater for python3 -m (module) vs python3 (file)
    from . import wrapped_carla as carla
except ImportError:
    import wrapped_carla as carla

_FPS = 24
_WIDTH = 640
_HEIGHT = 360
_SENSOR_BLUEPRINT_NAME = 'sensor.camera.rgb'
_TRANSFORM = carla.Transform(
    carla.Location(-15, 0, 15),
    carla.Rotation(16.875, 0, 0)
)


def _to_bgra_array(image: carla.Image):
    array = numpy.frombuffer(image.raw_data, dtype=numpy.dtype("uint8"))
    array = numpy.reshape(array, (image.height, image.width, 4))

    return array


def _to_rgb_array(image: carla.Image):
    array = _to_bgra_array(image)
    array = array[:, :, :3]
    array = array[:, :, ::-1]

    return array


def create_sensor(
        client: carla.Client,
        actor_id: int,
        sensor_blueprint_name: str = _SENSOR_BLUEPRINT_NAME,
        fps: int = _FPS,
        width: int = _WIDTH,
        height: int = _HEIGHT,
        transform: carla.Transform = _TRANSFORM) -> carla.ServerSideSensor:
    world = client.get_world()
    world.wait_for_tick()

    actor = world.get_actor(actor_id)
    world.wait_for_tick()

    blueprint_library = world.get_blueprint_library()
    sensor_blueprint = blueprint_library.find(sensor_blueprint_name)
    sensor_blueprint.set_attribute('sensor_tick', str(1.0 / fps))
    sensor_blueprint.set_attribute('image_size_x', str(width))
    sensor_blueprint.set_attribute('image_size_y', str(height))
    sensor = world.spawn_actor(
        sensor_blueprint,
        transform,
        attach_to=actor,
        attachment_type=carla.AttachmentType.SpringArm
    )
    world.wait_for_tick()

    print(sensor)

    return sensor
