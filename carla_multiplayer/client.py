import pygame

from .controller import GamepadController
from .screen import Screen, _FPS, _WIDTH, _HEIGHT
from .udp import Sender, Receiver

_CONTROLLER_INDEX = 0
_QUEUE_SIZE = 2


class Client(object):
    def __init__(self,
            host: str,
            controller_port: int,
            screen_port: int,
            controller_index: int = _CONTROLLER_INDEX,
            fps: int = _FPS,
            width: int = _WIDTH,
            height: int = _HEIGHT,
            queue_size: int = _QUEUE_SIZE):
        self._host: str = host
        self._controller_port: int = controller_port
        self._screen_port: int = screen_port
        self._controller_index: int = controller_index
        self._fps: int = fps
        self._width: int = width
        self._height: int = height
        self._queue_size: int = queue_size

        pygame.init()

        self._sender: Sender = Sender(self._controller_port, self._queue_size, use_shared_socket=True)
        self._controller: GamepadController = GamepadController(self._sender, self._host, self._controller_port, self._controller_index)
        self._receiver: Receiver = Receiver(self._screen_port, self._queue_size, use_shared_socket=True)
        self._screen: Screen = Screen(self._width, self._height)
        self._receiver.set_callback(self._screen.handle_webp_bytes)
        self._clock: pygame.time.Clock = pygame.time.Clock()

        self._stopped = False

    def start(self):
        self._sender.start()
        self._controller.start()
        self._receiver.start()

    def run(self):
        while not self._stopped:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._stopped = True
                        break

                    self._controller.handle_event(event)

                self._screen.update()

                self._clock.tick(self._fps)
            except KeyboardInterrupt:
                self._stopped = True
                break

    def stop(self):
        try:
            self._receiver.stop()
        except Exception:
            pass

        try:
            self._controller.stop()
        except Exception:
            pass

        try:
            self._sender.stop()
        except Exception:
            pass


def run_client(host: str,
        port: int,
        controller_index: int = _CONTROLLER_INDEX,
        fps: int = _FPS,
        width: int = _WIDTH,
        height: int = _HEIGHT,
        queue_size: int = _QUEUE_SIZE):
    client = Client(
        host=host,
        controller_index=controller_index,
        controller_port=port,
        screen_port=port,
        fps=fps,
        width=width,
        height=height,
        queue_size=queue_size
    )

    client.start()
    client.run()
    client.stop()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('--host', type=str, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--controller-index', type=int, default=0)
    parser.add_argument('--fps', type=int, default=_FPS)
    parser.add_argument('--width', type=int, default=_WIDTH)
    parser.add_argument('--height', type=int, default=_WIDTH)
    parser.add_argument('--queue-size', type=int, default=_QUEUE_SIZE)

    args = parser.parse_args()

    run_client(
        host=args.host,
        port=args.port,
        controller_index=args.controller_index,
        fps=args.fps,
        width=args.width,
        height=args.height,
        queue_size=args.queue_size,
    )
