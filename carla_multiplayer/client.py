from typing import Optional

import Pyro4
import pygame

from .controller import GamepadController, ControllerState
from .screen import Screen
from .server import Server, Player

_CONTROLLER_INDEX = 0
_WIDTH = 640
_HEIGHT = 480

Pyro4.config.SERIALIZER = 'pickle'


class Client(object):
    def __init__(self, host: str):
        self._host: str = host

        self._screen: Screen = Screen(_WIDTH, _HEIGHT)
        self._controller: GamepadController = GamepadController(_CONTROLLER_INDEX, self._controller_callback)

        self._server: Optional[Server] = None
        self._uuid: Optional[str] = None
        self._player: Optional[Player] = None

        self._stopped: bool = False

    def _controller_callback(self, controller_state: ControllerState):
        if self._player is None:
            return

        self._player.apply_control(
            throttle=controller_state.throttle,
            steer=controller_state.steer,
            brake=controller_state.brake,
            hand_brake=controller_state.hand_brake,
            reverse=controller_state.reverse
        )

    def start(self):
        self._stopped = False

        self._server = Pyro4.Proxy('PYRO:carla_multiplayer@{}:13337'.format(self._host))
        self._uuid = self._server.register_player()
        self._player = self._server.get_proxy_player(self._uuid)

    def handle_event(self, event: pygame.event.EventType):
        self._controller.handle_event(event)

    def update(self):
        self._screen.update()

    def stop(self):
        self._stopped = True

        if self._uuid is not None and self._server is not None:
            self._server.unregister_player(self._uuid)


if __name__ == '__main__':
    import sys
    import traceback

    try:
        _host = sys.argv[1]
    except Exception:
        raise SystemExit('error: first argument must be address of address to connect to')

    pygame.init()
    pygame.font.init()
    pygame.joystick.init()

    _client = Client(_host)

    print('connecting')

    try:
        _client.start()
    except Exception:
        print('caught {}; traceback follows')

        traceback.print_exc()

    clock = pygame.time.Clock()

    stopped = False
    while not stopped:
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    stopped = True
                    break

                _client.handle_event(event)

            _client.update()

            clock.tick(24)
        except KeyboardInterrupt:
            break

    print('disconnecting')

    _client.stop()
