# Name: Wildrose
# Created By: Karlo Tsutskiridze
# Date: 03-17-2024

import pygame as pg
import characters as chr
import constants as c

class WildroseMixer:
    def __init__(self, bg_music=None):
        pg.mixer.init()
        pg.mixer.set_num_channels(4)
        self._bg_music_channel = pg.mixer.Channel(1)
        self._bg_music = pg.mixer.Sound("static/faraon-harold-budd.wav" if bg_music is None else bg_music)
    def _load_music(self, music): pg.mixer.music.load(music)
    def toggle_background_music(self):
        if self._bg_music_channel.get_busy(): self._bg_music_channel.pause()
        else: self._bg_music_channel.unpause()
    def play_background_music(self, loops=1): self._bg_music_channel.play(self._bg_music, loops=loops, fade_ms=2000)

class WildroseGame:
    WIDTH = 400
    HEIGHT = 400

    def __init__(self):
        pg.init()
        pg.display.set_caption("Wildrose")
        # init mixer
        self.mixer = WildroseMixer(bg_music="static/faraon-harold-budd.wav")
        # this is the main window
        self.window = pg.display.set_mode((self.WIDTH, self.HEIGHT))
        self.clock = pg.time.Clock()
        # Performance optimization
        pg.event.set_allowed([pg.QUIT, pg.KEYDOWN, pg.KEYUP, pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP, pg.MOUSEMOTION])
        self.running = False
        # this is the character
        self.white_car = chr.WhiteCar(root_surface=self.window, sprite_scale=16.0, fill_width=False)
        self.mouse_down = False
    def _start_mixer(self): self.mixer.play_background_music(loops=-1)
    def _set_running(self, running=False): self.running = running
    def _quit(self, ): pg.quit()
    def _fill_background(self, color): self.window.fill(color)
    def _handle_events(self):
        for event in pg.event.get():
            self.white_car.handle_event(event)
            if event.type == pg.QUIT: self._set_running(False)
            elif event.type == pg.MOUSEBUTTONDOWN: self.mouse_down = True
            elif event.type == pg.MOUSEBUTTONUP: self.mouse_down = False
            elif event.type == pg.MOUSEMOTION:
                if self.mouse_down: self.white_car.set_action(action=character.ST_DAMAGE)
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_q: self._set_running(False)
                elif event.key == pg.K_ESCAPE: self.mixer.toggle_background_music()
    def start(self):
        self._set_running(True)
        self._start_mixer()
        while self.running:
            # handle events
            self._handle_events()
            self._fill_background(c.Color.BLACK.value)
            # display white car
            self.white_car.display()
            pg.display.update()
            self.clock.tick(60)
        self._quit()

if __name__ == "__main__": WildroseGame().start()
