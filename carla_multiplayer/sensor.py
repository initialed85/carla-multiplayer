try:
    from .wrapped_carla import *
    print(1)
except ImportError:
    from wrapped_carla import *
    print(2)


class Sensor(object):
    def __init__(self):
        pass
