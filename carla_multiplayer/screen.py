from io import BytesIO

import pygame
from PIL import Image


class Screen(object):
    def __init__(self, port, width, height):
        self._port = port
        self._width = width
        self._height = height

        self._dimensions = (self._width, self._height)

        self._screen = pygame.display.set_mode(
            self._dimensions,
            pygame.HWSURFACE | pygame.DOUBLEBUF
        )

        self._image = None

    def handle_image(self, data):
        temp_input = BytesIO()
        temp_input.write(data)
        pil_image = Image.open(temp_input)
        if pil_image.size != self._dimensions:
            pil_image = pil_image.resize(self._dimensions)

        self._image = pygame.image.fromstring(pil_image.tobytes(), pil_image.size, pil_image.mode)

    def update(self):
        if self._image is None:
            return

        self._screen.blit(self._image, (0, 0))
        pygame.display.flip()


if __name__ == '__main__':
    pygame.init()
    pygame.font.init()

    screen = Screen(
        port=13337,
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

    screen.stop()
    pygame.quit()
