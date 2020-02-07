from typing import Union

import Pyro4
import pygame

from .controller import GamepadController, RateLimiter
from .screen import Screen
from .udp import Receiver
from .vehicle import Vehicle

if __name__ == '__main__':
    import sys

    _vehicle: Union[Vehicle, Pyro4.Proxy] = Pyro4.Proxy('PYRO:vehicle@{}:13337'.format(sys.argv[1]))

    _rate_limiter = RateLimiter(_vehicle.apply_control)
    _rate_limiter.start()

    _controller = GamepadController(int(sys.argv[2]), _rate_limiter.set_value)

    _receiver = Receiver(int(sys.argv[3]), 8)

    _screen = Screen(1280, 720, _receiver)

    _receiver.set_callback(_screen.handle_webp_bytes)
    _receiver.start()

    pygame.init()
    _clock = pygame.time.Clock()

    _stopped = False
    while not _stopped:
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    _stopped = True
                    break

                _controller.handle_event(event)

            _screen.update()

            _clock.tick(24)
        except KeyboardInterrupt:
            break

    _rate_limiter.stop()
    _receiver.stop()
    pygame.quit()
