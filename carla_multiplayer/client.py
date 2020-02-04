import datetime
import time
from threading import Thread
from typing import Optional
from uuid import UUID

import Pyro4
import pygame

from .controller import GamepadController, ControllerState
from .screen import Screen
from .server import Server, Player

_CONTROLLER_INDEX = 0
_WIDTH = 1280
_HEIGHT = 720
_FPS = 30
_CONTROL_RATE = 10

Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.COMPRESSION = True


class Client(object):
    def __init__(self, host: str):
        self._host: str = host

        self._screen: Screen = Screen(_WIDTH, _HEIGHT)
        self._controller: GamepadController = GamepadController(_CONTROLLER_INDEX, self._controller_callback)

        self._server: Optional[Server] = None
        self._uuid: Optional[UUID] = None
        self._player: Optional[Player] = None

        self._controller_state: Optional[ControllerState] = None

        self._frame_getter: Optional[Thread] = None
        self._controls_applicator: Optional[Thread] = None

        self._stopped: bool = False

    @staticmethod
    def _sleep(started: datetime.datetime, iteration: datetime.timedelta):
        target = started + iteration
        now = datetime.datetime.now()
        if now > target:
            return

        time.sleep((target - now).total_seconds())

    def _get_frames(self):
        iteration = datetime.timedelta(seconds=1.0 / (float(_FPS)))

        while not self._stopped:
            started = datetime.datetime.now()
            if self._player is None:
                self._sleep(started, iteration)

                continue

            before_1 = datetime.datetime.now()
            frame = self._player.get_frame()
            after_1 = datetime.datetime.now()

            before_2 = datetime.datetime.now()
            self._screen.handle_image(frame)
            after_2 = datetime.datetime.now()

            print('got frame in {}; handled it in {}'.format(
                after_1 - before_1,
                after_2 - before_2
            ))

            self._sleep(started, iteration)

    def _apply_controls(self):
        iteration = datetime.timedelta(seconds=1.0 / (float(_CONTROL_RATE)))

        while not self._stopped:
            started = datetime.datetime.now()
            if self._player is None or self._controller_state is None:
                self._sleep(started, iteration)

                continue

            self._player.apply_control(
                throttle=self._controller_state.throttle,
                steer=self._controller_state.steer,
                brake=self._controller_state.brake,
                hand_brake=self._controller_state.hand_brake,
                reverse=self._controller_state.reverse
            )

            self._sleep(started, iteration)

    def _controller_callback(self, controller_state: ControllerState):
        if self._player is None:
            return

        self._controller_state = controller_state

    def start(self):
        self._stopped = False

        self._frame_getter = Thread(target=self._get_frames)
        self._frame_getter.start()

        self._controls_applicator = Thread(target=self._apply_controls)
        self._controls_applicator.start()

        self._server = Pyro4.Proxy('PYRO:carla_multiplayer@{}:13337'.format(self._host))
        self._uuid = self._server.register_player()
        self._player = self._server.get_proxy_player(self._uuid)

    def handle_event(self, event: pygame.event.EventType):
        self._controller.handle_event(event)

    def update(self):
        try:
            self._screen.update()
        except Exception:
            pass

    def stop(self):
        self._stopped = True

        if self._frame_getter is not None:
            try:
                self._frame_getter.join()
            except RuntimeError:
                pass

        if self._controls_applicator is not None:
            try:
                self._controls_applicator.join()
            except RuntimeError:
                pass

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

        raise SyntaxError('error: failed to start client')

    clock = pygame.time.Clock()

    print('connected')

    stopped = False
    while not stopped:
        try:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    stopped = True
                    break

                _client.handle_event(e)

            _client.update()

            clock.tick(_FPS * 2)
        except KeyboardInterrupt:
            break

    print('disconnecting')

    _client.stop()
