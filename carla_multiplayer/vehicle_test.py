import unittest

from mock import Mock, call

from .vehicle import create_vehicle, carla, get_vehicle, delete_vehicle

_TRANSFORM = carla.Transform(
    carla.Location(-15, 0, 15),
    carla.Rotation(16.875, 0, 0)
)


class VehicleFunctionTest(unittest.TestCase):
    def test_create_vehicle(self):
        client = Mock()
        actor = Mock()
        client.get_world.return_value.get_actor.return_value = actor

        vehicle_blueprint = Mock()
        client.get_world.return_value.get_blueprint_library.return_value.find.return_value = vehicle_blueprint

        vehicle = Mock()
        client.get_world.return_value.spawn_actor.return_value = vehicle

        created_vehicle = create_vehicle(client, 'vehicle.komatsu.830e', _TRANSFORM)

        self.assertEqual(vehicle, created_vehicle)

        self.assertEqual(
            [call.get_world(),
                call.get_world().wait_for_tick(),
                call.get_world().get_blueprint_library(),
                call.get_world().get_blueprint_library().find('vehicle.komatsu.830e'),
                call.get_world().spawn_actor(vehicle_blueprint, _TRANSFORM),
                call.get_world().wait_for_tick()],
            client.mock_calls
        )

    def test_get_vehicle(self):
        client = Mock()
        vehicle = Mock()
        client.get_world.return_value.get_actor.return_value = vehicle

        got_vehicle = get_vehicle(client, 2)

        self.assertEqual(
            vehicle, got_vehicle
        )

        self.assertEqual(
            [call.get_world(),
                call.get_world().wait_for_tick(),
                call.get_world().get_actor(2),
                call.get_world().wait_for_tick()],
            client.mock_calls
        )

    def test_delete_vehicle(self):
        client = Mock()
        vehicle = Mock()
        vehicle.id = 2
        client.get_world.return_value.get_actor.return_value = vehicle

        delete_vehicle(client, vehicle.id)

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


class VehicleTest(unittest.TestCase):
    pass  # TODO: hard to implement without a running Carla instance
