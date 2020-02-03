import socket
from io import BytesIO
from threading import Thread

import pygame
from PIL import Image


class Screen(object):
    def __init__(self, port, width, height):
        self._port = port
        self._width = width
        self._height = height

        self._dimensions = (self._width, self._height)

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(1.0)
        self._socket.bind(('', self._port))

        self._screen = pygame.display.set_mode(
            self._dimensions,
            pygame.HWSURFACE | pygame.DOUBLEBUF
        )

        self._image = None

        self._stopped = False
        self._images_handler = Thread(target=self.handle_images)
        self._images_handler.start()

    def handle_image(self, data):
        temp_input = BytesIO()
        temp_input.write(data)
        pil_image = Image.open(temp_input)
        if pil_image.size != self._dimensions:
            pil_image = pil_image.resize(self._dimensions)

        self._image = pygame.image.fromstring(pil_image.tobytes(), pil_image.size, pil_image.mode)

    def handle_images(self):
        while not self._stopped:
            try:
                data, addr = self._socket.recvfrom(65536)
            except socket.timeout:
                continue

            self.handle_image(data)

    def update(self):
        if self._image is None:
            return

        self._screen.blit(self._image, (0, 0))
        pygame.display.flip()

    def stop(self):
        self._stopped = True
        self._images_handler.join()


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
