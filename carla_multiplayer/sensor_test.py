import unittest

from mock import Mock, call

from .sensor import create_sensor, _TRANSFORM, carla, get_sensor, delete_sensor


class SensorFunctionTest(unittest.TestCase):
    def test_create_sensor(self):
        client = Mock()
        actor = Mock()
        client.get_world.return_value.get_actor.return_value = actor

        sensor_blueprint = Mock()
        client.get_world.return_value.get_blueprint_library.return_value.find.return_value = sensor_blueprint

        sensor = Mock()
        client.get_world.return_value.spawn_actor.return_value = sensor

        created_sensor = create_sensor(client, 2)

        self.assertEqual(sensor, created_sensor)

        self.assertEqual(
            [call.get_world(),
                call.get_world().wait_for_tick(),
                call.get_world().get_actor(2),
                call.get_world().wait_for_tick(),
                call.get_world().get_blueprint_library(),
                call.get_world().get_blueprint_library().find('sensor.camera.rgb'),
                call.get_world().get_blueprint_library().find().set_attribute('sensor_tick', '0.041666666666666664'),
                call.get_world().get_blueprint_library().find().set_attribute('image_size_x', '640'),
                call.get_world().get_blueprint_library().find().set_attribute('image_size_y', '360'),
                call.get_world().spawn_actor(sensor_blueprint, _TRANSFORM, attach_to=actor, attachment_type=carla.AttachmentType.SpringArm),
                call.get_world().wait_for_tick()],
            client.mock_calls
        )

    def test_get_sensor(self):
        client = Mock()
        sensor = Mock()
        client.get_world.return_value.get_actor.return_value = sensor

        got_sensor = get_sensor(client, 2)

        self.assertEqual(
            sensor, got_sensor
        )

        self.assertEqual(
            [call.get_world(),
                call.get_world().wait_for_tick(),
                call.get_world().get_actor(2),
                call.get_world().wait_for_tick()],
            client.mock_calls
        )

    def test_delete_sensor(self):
        client = Mock()
        sensor = Mock()
        sensor.id = 2
        client.get_world.return_value.get_actor.return_value = sensor

        delete_sensor(client, sensor.id)

        self.assertEqual(
            [call.get_world(),
                call.get_world().wait_for_tick(),
                call.get_world().get_actor(2),
                call.get_world().wait_for_tick(),
                call.get_world().get_actor().destroy(),
                call.get_world(),
                call.get_world().wait_for_tick()],
            client.mock_calls
        )


class SensorTest(unittest.TestCase):
    pass  # TODO: hard to implement without a running Carla instance
