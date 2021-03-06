import os
import sys

sys.path.append(
    '{}/carla-0.9.6-py3.6-linux-x86_64.egg'.format(
        os.path.dirname(os.path.realpath(__file__))
    )
)

try:
    from carla import *
except ImportError as e:
    try:
        from .carla import *
    except ImportError as e:  # hack for platforms that don't support or don't have Carla
        print('warning: failed to import carla because {}; objects are mocked'.format(repr(e)))

    from mock import MagicMock

    Actor = MagicMock()
    ActorAttribute = MagicMock()
    ActorAttributeType = MagicMock()
    ActorBlueprint = MagicMock()
    ActorList = MagicMock()
    ActorSnapshot = MagicMock()
    AttachmentType = MagicMock()
    BlueprintLibrary = MagicMock()
    BoundingBox = MagicMock()
    Client = MagicMock()
    ClientSideSensor = MagicMock()
    CollisionEvent = MagicMock()
    Color = MagicMock()
    ColorConverter = MagicMock()
    DebugHelper = MagicMock()
    GearPhysicsControl = MagicMock()
    GeoLocation = MagicMock()
    GnssEvent = MagicMock()
    GnssSensor = MagicMock()
    Image = MagicMock()
    LaneChange = MagicMock()
    LaneInvasionEvent = MagicMock()
    LaneInvasionSensor = MagicMock()
    LaneMarking = MagicMock()
    LaneMarkingColor = MagicMock()
    LaneMarkingType = MagicMock()
    LaneType = MagicMock()
    LidarMeasurement = MagicMock()
    Location = MagicMock()
    Map = MagicMock()
    ObstacleDetectionEvent = MagicMock()
    Rotation = MagicMock()
    Sensor = MagicMock()
    SensorData = MagicMock()
    ServerSideSensor = MagicMock()
    Timestamp = MagicMock()
    TrafficLight = MagicMock()
    TrafficLightState = MagicMock()
    TrafficSign = MagicMock()
    Transform = MagicMock()
    Vector2D = MagicMock()
    Vector3D = MagicMock()
    Vehicle = MagicMock()
    VehicleControl = MagicMock()
    VehiclePhysicsControl = MagicMock()
    Walker = MagicMock()
    WalkerAIController = MagicMock()
    WalkerBoneControl = MagicMock()
    WalkerControl = MagicMock()
    Waypoint = MagicMock()
    WeatherParameters = MagicMock()
    WheelPhysicsControl = MagicMock()
    World = MagicMock()
    WorldSettings = MagicMock()
    WorldSnapshot = MagicMock()
    command = MagicMock()
    libcarla = MagicMock()
    vector_of_gears = MagicMock()
    vector_of_ints = MagicMock()
    vector_of_vector2D = MagicMock()
    vector_of_wheels = MagicMock()
