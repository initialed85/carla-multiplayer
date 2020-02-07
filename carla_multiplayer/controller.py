from typing import NamedTuple


class ControllerState(NamedTuple):
    throttle: float
    brake: float
    steer: float
    hand_brake: bool
    reverse: bool
    reset: bool


def handle_steer_deadzone(steer):
    if -0.16 <= steer <= 0.16:
        steer = 0.0

    return steer
