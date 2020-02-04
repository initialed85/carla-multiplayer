from typing import Callable, Dict, Tuple, Optional
from typing import NamedTuple

import pygame


class RawControllerState(NamedTuple):
    axis_data: Dict[int, Optional[float]] = {}
    button_data: Dict[int, bool] = {}
    hat_data: Dict[int, Tuple[int, int]] = {}


class ControllerEventHandler(object):
    def __init__(self, callback: Callable):
        self._callback: Callable = callback

        self._controller: pygame.joystick.JoystickType = pygame.joystick.Joystick(0)
        self._controller.init()

        self._axis_data: Dict[int, Optional[float]] = {
            i: None for i in range(0, self._controller.get_numaxes())
        }

        self._button_data: Dict[int, bool] = {
            i: False for i in range(0, self._controller.get_numbuttons())
        }

        self._hat_data: Dict[int, Tuple[int, int]] = {
            i: (0, 0) for i in range(0, self._controller.get_numhats())
        }

    def handle_event(self, event: pygame.event.EventType):
        if event.type == pygame.JOYAXISMOTION:
            self._axis_data[event.axis] = round(event.value, 2)
        elif event.type == pygame.JOYBUTTONDOWN:
            self._button_data[event.button] = True
        elif event.type == pygame.JOYBUTTONUP:
            self._button_data[event.button] = False
        elif event.type == pygame.JOYHATMOTION:
            self._hat_data[event.hat] = event.value
        else:
            return

        if not callable(self._callback):
            raise TypeError('expected {}} to be callable but was {}'.format(
                repr(self._callback),
                type(self._callback)
            ))

        self._callback(
            RawControllerState(
                axis_data=self._axis_data,
                button_data=self._button_data,
                hat_data=self._hat_data
            )
        )


class ControllerState(NamedTuple):
    throttle: float
    brake: float
    steer: float
    hand_brake: bool
    reverse: bool


class Controller(object):
    def __init__(self, callback: Callable):
        self._callback: Callable = callback

        self._handler: ControllerEventHandler = ControllerEventHandler(self._handle_callback)

        self._reverse: bool = False

    def _handle_callback(self, controller_state: RawControllerState):
        raise NotImplementedError('this method should be overridden')

    def handle_event(self, event: pygame.event.EventType):
        self._handler.handle_event(event)


class PS4Controller(Controller):
    def _handle_callback(self, controller_state: RawControllerState):
        if controller_state.axis_data[5] is not None:
            throttle = round((controller_state.axis_data[5] + 1.0) / 2.0, 2)
        else:
            throttle = 0.0

        if controller_state.axis_data[4] is not None:
            brake = round((controller_state.axis_data[4] + 1.0) / 2.0, 2)
        else:
            brake = 0.0

        if controller_state.axis_data[0] is not None:
            steer = round(controller_state.axis_data[0], 2)
        else:
            steer = 0.0

        hand_brake = controller_state.button_data[0]

        select_forward = controller_state.button_data[11] is True
        select_reverse = controller_state.button_data[12] is True

        if select_forward:
            self._reverse = False
        elif select_reverse:
            self._reverse = True

        if -0.05 <= steer <= 0.05:
            steer = 0.0

        if not callable(self._callback):
            raise TypeError('expected {}} to be callable but was {}'.format(
                repr(self._callback),
                type(self._callback)
            ))

        self._callback(
            ControllerState(
                throttle=throttle,
                brake=brake,
                steer=steer,
                hand_brake=hand_brake,
                reverse=self._reverse
            )
        )


if __name__ == '__main__':
    def callback(controller_state: ControllerState):
        print(controller_state)

        return


    pygame.init()
    pygame.joystick.init()

    controller = PS4Controller(callback)

    clock = pygame.time.Clock()

    stopped = False
    while not stopped:
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    stopped = True
                    break

                controller.handle_event(event)

            clock.tick(24)
        except KeyboardInterrupt:
            break

    pygame.quit()
