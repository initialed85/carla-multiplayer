import os
import sys

sys.path.append('{}/carla-0.9.6-py3.6-linux-x86_64.egg'.format(
    os.path.dirname(os.path.realpath(__file__)))
)

from carla import *
