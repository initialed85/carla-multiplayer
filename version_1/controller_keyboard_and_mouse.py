from typing import Callable, Dict, Optional, Tuple
from typing import NamedTuple

import pygame

from .controller import ControllerState, handle_steer_deadzone


class RawControllerState(NamedTuple):
    cursor_data: Optional[Tuple[int, int]] = None
    button_data: Dict[int, bool] = {}
    key_data: Dict[int, bool] = {}


class ControllerEventHandler(object):
    def __init__(self, callback: Callable):
        self._callback: Callable = callback

        self._cursor_data: Optional[Tuple[int, int]] = None

        self._button_data: Dict[int, bool] = {
            i: False for i in range(0, 4)
        }

        self._key_data: Dict[int, bool] = {
            i: False for i in range(0, 128)
        }

    def handle_event(self, event: pygame.event.EventType):
        if event.type == pygame.MOUSEMOTION:
            self._cursor_data = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._button_data[event.button] = True
            pygame.event.set_grab(True)
            pygame.mouse.set_visible(False)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._button_data[event.button] = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.event.set_grab(False)
                pygame.mouse.set_visible(True)
            else:
                self._key_data[event.key] = True
        elif event.type == pygame.KEYUP:
            if event.key != pygame.K_ESCAPE:
                self._key_data[event.key] = False
        else:
            return

        if not callable(self._callback):
            raise TypeError('expected {}} to be callable but was {}'.format(
                repr(self._callback),
                type(self._callback)
            ))

        self._callback(
            RawControllerState(
                cursor_data=self._cursor_data,
                button_data=self._button_data,
                key_data=self._key_data
            )
        )


class KeyboardAndMouseController(object):
    def __init__(self, callback: Callable, width: int, height: int):
        self._callback: Callable = callback
        self._width = width
        self._height = height

        self._handler: ControllerEventHandler = ControllerEventHandler(
            callback=self._callback_wrapper,
        )

        self._reverse: bool = False

        self._last_controller_state: Optional[ControllerState] = None

    def _callback_wrapper(self, raw_controller_state: RawControllerState):
        controller_state = self._handle_callback(raw_controller_state)
        if controller_state == self._last_controller_state:
            return

        self._callback(controller_state)

        self._last_controller_state = controller_state

    def _handle_callback(self, controller_state: RawControllerState):
        if controller_state.button_data[1] is not None:
            throttle = 1.0 if controller_state.button_data[1] else 0.0
        else:
            throttle = 0.0

        if controller_state.button_data[3] is not None:
            brake = 1.0 if controller_state.button_data[3] else 0.0
        else:
            brake = 0.0

        if controller_state.cursor_data is not None:
            steer = ((controller_state.cursor_data[0] / (self._width - 1)) - 0.5) * 2
        else:
            steer = 0.0

        hand_brake = controller_state.key_data.get(pygame.K_SPACE, False)

        select_forward = controller_state.key_data.get(pygame.K_UP) is True
        select_reverse = controller_state.key_data.get(pygame.K_DOWN) is True

        if select_forward:
            self._reverse = False
        elif select_reverse:
            self._reverse = True

        reset = controller_state.key_data.get(pygame.K_r, False)

        if -0.16 <= steer <= 0.16:
            steer = 0.0

        if not callable(self._callback):
            raise TypeError('expected {}} to be callable but was {}'.format(
                repr(self._callback),
                type(self._callback)
            ))

        return ControllerState(
            throttle=throttle,
            brake=brake,
            steer=handle_steer_deadzone(steer),
            hand_brake=hand_brake,
            reverse=self._reverse,
            reset=reset,
        )

    def handle_event(self, event: pygame.event.EventType):
        self._handler.handle_event(event)


if __name__ == '__main__':
    def _callback(controller_state: ControllerState):
        print('meat', controller_state)

        return


    pygame.init()

    pygame.display.set_mode(
        (1280, 720),
        pygame.HWSURFACE | pygame.DOUBLEBUF
    )

    _controller = KeyboardAndMouseController(
        callback=_callback,
        width=1280,
        height=720
    )

    _clock = pygame.time.Clock()

    _stopped = False
    while not _stopped:
        try:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    _stopped = True
                    break

                _controller.handle_event(e)

            _clock.tick(24)
        except KeyboardInterrupt:
            break

    pygame.quit()
