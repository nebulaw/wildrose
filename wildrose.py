# Name: Wildrose
# Created By: Karlo Tsutskiridze
# Date: 03-17-2024

import pygame as pg
from characters import character

# TODO: create queue for actions
#       support for intelligent queueing these actions
#       and clearing it if necessary

class WGColor:
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)


class WildroseGame:
    WIDTH = 400
    HEIGHT = 400

    def __init__(self):
        pg.init()
        # this is the main window
        self.window = pg.display.set_mode((self.WIDTH, self.HEIGHT))
        pg.display.set_caption("Wildrose")
        self.clock = pg.time.Clock()
        self.running = False
        # this is the character
        self.white_car = character.WhiteCar()
        self.mouse_down = False

    def __set_running(self, running=False):
        self.running = running

    def __quit(self, ):
        pg.quit()

    def __fill_background(self, color):
        self.window.fill(color)

    def __handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.__set_running(False)
            elif event.type == pg.MOUSEBUTTONDOWN:
                self.mouse_down = True
            elif event.type == pg.MOUSEBUTTONUP:
                self.mouse_down = False
                self.white_car.set_action(action=character.ST_IDLE)
            elif event.type == pg.MOUSEMOTION:
                if self.mouse_down:
                    self.white_car.set_action(action=character.ST_DAMAGE)
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_q:
                    self.__set_running(False)
                elif event.key == pg.K_k:
                    self.white_car.set_action(character.ST_DIE)
        pass

    def start(self):
        self.__set_running(True)
        while self.running:
            # handle events
            self.__handle_events()

            self.__fill_background(WGColor.BLACK)

            # display white car
            self.white_car.display(self.window, )

            pg.display.update()
            self.clock.tick(60)
        self.__quit()


WildroseGame().start()

