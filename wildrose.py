# Name: Wildrose
# Created By: Karlo Tsutskiridze
# Date: 03-17-2024

import pygame as pg
from characters import character
import constants as c

class WildroseGame:
    WIDTH = 400
    HEIGHT = 400

    def __init__(self):
        pg.init()
        pg.display.set_caption("Wildrose")
        # init mixer
        pg.mixer.init()
        pg.mixer.set_num_channels(8)
        self.bg_music_playing = False
        # this is the main window
        self.window = pg.display.set_mode((self.WIDTH, self.HEIGHT))
        self.clock = pg.time.Clock()
        self.running = False
        # this is the character
        self.white_car = character.WhiteCar(root_surface=self.window, fill_width=True)
        self.mouse_down = False

    def __toggle_background_music(self):
        if self.bg_music_playing:
            pg.mixer.music.pause()
            self.bg_music_playing = False
        else:
            pg.mixer.music.unpause()
            self.bg_music_playing = True

    def __play_background_music(self):
        pg.mixer.music.load('static/faraon-harold-budd.wav')
        pg.mixer.music.play(-1)
        self.bg_music_playing = True

    def __set_running(self, running=False):
        self.running = running

    def __quit(self, ):
        pg.quit()

    def __fill_background(self, color):
        self.window.fill(color)

    def __handle_events(self):
        for event in pg.event.get():
            self.white_car.handle_event(event)
            if event.type == pg.QUIT:
                self.__set_running(False)
            elif event.type == pg.MOUSEBUTTONDOWN:
                self.mouse_down = True
            elif event.type == pg.MOUSEBUTTONUP:
                self.mouse_down = False
            elif event.type == pg.MOUSEMOTION:
                if self.mouse_down:
                    self.white_car.set_action(action=character.ST_DAMAGE)
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_q:
                    self.__set_running(False)
                elif event.key == pg.K_ESCAPE:
                    self.__toggle_background_music()
        pass

    def start(self):
        self.__set_running(True)
        self.__play_background_music()
        while self.running:
            # handle events
            self.__handle_events()

            self.__fill_background(c.Color.BLACK.value)

            # display white car
            self.white_car.display()

            pg.display.update()
            self.clock.tick(60)
        self.__quit()


if __name__ == "__main__":
    WildroseGame().start()

