from io import BytesIO
from typing import Tuple, Optional

import pygame
from PIL import Image


class Screen(object):
    def __init__(self, width: int, height: int):
        self._width: int = width
        self._height: int = height

        self._dimensions: Tuple[int, int] = (self._width, self._height)

        self._screen: pygame.SurfaceType = pygame.display.set_mode(
            self._dimensions,
            pygame.HWSURFACE | pygame.DOUBLEBUF
        )

        self._last_image: Image.Image = Optional[None]
        self._image: Image.Image = Optional[None]

    def handle_image(self, data: bytes):
        buffer = BytesIO()
        buffer.write(data)
        pil_image = Image.open(buffer)
        if pil_image.size != self._dimensions:
            pil_image = pil_image.resize(self._dimensions)

        self._image = pygame.image.fromstring(pil_image.tobytes(), pil_image.size, pil_image.mode)

    def update(self):
        if self._image is None:
            return

        if self._image == self._last_image:
            return

        self._screen.blit(self._image, (0, 0))
        pygame.display.flip()

        self._last_image = self._image


if __name__ == '__main__':
    pygame.init()
    pygame.font.init()

    screen = Screen(
        width=640,
        height=480
    )

    clock = pygame.time.Clock()

    stopped = False
    while not stopped:
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    stopped = True
                    break

            screen.update()

            clock.tick(24)
        except KeyboardInterrupt:
            break

    pygame.quit()
