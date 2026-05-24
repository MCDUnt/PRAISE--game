import sys
import time
import pygame
from renderers import IRenderer



class ConsoleRenderer(IRenderer):
    def __init__(self):
        self.environment_statebuffer = {}


    def observe(self, statebuffer):
        self.environment_statebuffer = statebuffer

    def render(self):
        state = self.environment_statebuffer.get_state()
        if state:
            data = []
            length = state["length"]
            for i in range(length):
                if i == state["agent_location"] and i in state["dirt_location"]:
                    data.append('#')
                elif i == state["agent_location"]:
                    data.append('o')
                elif i in state["dirt_location"]:
                    data.append('x')
                else:
                    data.append(' ')

            print(data)


class PyGameRenderer(IRenderer):
    def __init__(self):
        self.screen = None
        self.array = []
        self.environment_statebuffer = {}

    def observe(self, statebuffer):
        self.environment_statebuffer = statebuffer

    def _prepare_data(self):
        data = []
        if self.state:
            length = self.state["length"]
            for i in range(length):
                if i == self.state["agent_location"] and i in self.state["dirt_location"]:
                    data.append('#')
                elif i == self.state["agent_location"]:
                    data.append('o')
                elif i in self.state["dirt_location"]:
                    data.append('x')
                else:
                    data.append(' ')
            self.array = data
        else:
            self.array = None

    def _pygame_render(self):

        pygame.init()

        screen_width, screen_height = 600, 300
        screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Draw from Array")

        WHITE = (255, 255, 255)
        BLUE = (0, 0, 255)
        BROWN = (139, 69, 19)
        BLACK = (0, 0, 0)

        cell_width = screen_width // len(self.array)
        cell_height = screen_height

        def _draw_square(x, y):
            pygame.draw.rect(screen, BLACK, (x, y, cell_width, cell_height), 2)  # Draw border of square

        def _draw_element(value, x, y):
            if value == 'x' or value == '#':
                pygame.draw.circle(screen, BROWN, (x + 2 * cell_width // 9, y + 2 * cell_height // 9),
                                   min(cell_width,cell_height) // 16)
                pygame.draw.circle(screen, BROWN, (x + 5 * cell_width // 9, y + 5 * cell_height // 9),
                                   min(cell_width,cell_height) // 16)
                pygame.draw.circle(screen, BROWN, (x + 7 * cell_width // 9, y + 7 * cell_height // 9),
                                   min(cell_width,cell_height) // 16)
                pygame.draw.circle(screen, BROWN, (x + 6 * cell_width // 9, y + 3 * cell_height // 9),
                                   min(cell_width,cell_height) // 16)
                pygame.draw.circle(screen, BROWN, (x + 3 * cell_width // 9, y + 8 * cell_height // 9),
                                   min(cell_width,cell_height) // 16)

            if value == 'o' or value == '#':
                pygame.draw.circle(screen, BLUE, (x + cell_width // 2, y + cell_height // 2), min(cell_width,cell_height) // 10)

        screen.fill(WHITE)
        for index, value in enumerate(self.array):
            x = index * cell_width
            _draw_square(x, 0)
            _draw_element(value, x, 0)

        pygame.display.flip()

        # Event handling (PyGame-related)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        time.sleep(0.05)

    def render(self):
        self.state = self.environment_statebuffer.get_state()
        if self.state:
            self._prepare_data()
            self._pygame_render()