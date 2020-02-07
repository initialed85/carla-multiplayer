from io import BytesIO
from typing import Tuple, Optional

import pygame
from PIL import Image

from .udp import Receiver


def _convert_webp_bytes_to_pygame_image(data: bytes, dimensions):
    buffer = BytesIO()
    buffer.write(data)
    pil_image = Image.open(buffer)
    if pil_image.size != dimensions:
        pil_image = pil_image.resize(dimensions)

    return pygame.image.fromstring(pil_image.tobytes(), pil_image.size, pil_image.mode)


class Screen(object):
    def __init__(self, width: int, height: int, receiver: Receiver):
        super().__init__()

        self._width: int = width
        self._height: int = height
        self._receiver: Receiver = receiver

        self._dimensions: Tuple[int, int] = (self._width, self._height)

        pygame.font.init()
        self._screen: pygame.SurfaceType = pygame.display.set_mode(
            self._dimensions,
            pygame.HWSURFACE | pygame.DOUBLEBUF
        )

        self._image: Optional[Image.Image] = None

    def handle_webp_bytes(self, data):
        self._image = _convert_webp_bytes_to_pygame_image(data, self._dimensions)

    def update(self):
        if self._image is None:
            return

        self._screen.blit(self._image, (0, 0))
        pygame.display.flip()


if __name__ == '__main__':
    import sys

    _receiver = Receiver(int(sys.argv[1]), 8)

    _screen = Screen(1280, 720, _receiver)

    _receiver.set_callback(_screen.handle_webp_bytes)
    _receiver.start()

    _clock = pygame.time.Clock()

    _stopped = False
    while not _stopped:
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    _stopped = True
                    break

            _screen.update()

            _clock.tick(24)
        except KeyboardInterrupt:
            break

    pygame.quit()
    _receiver.stop()
