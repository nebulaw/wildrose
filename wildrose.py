# Name: Wildrose
# Created By: Karlo Tsutskiridze
# Date: 03-17-2024

import pygame as pg

# TODO: create queue for actions
#       support for intelligent queueing these actions
#       and clearing it if necessary

class WGColor:
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)

class WhiteCar():
    WIDTH = 32
    HEIGHT = 32
    SCALE = 5
    COLORKEY = (0, 0, 0)

    ST_IDLE = 0
    ST_RUN = 1
    ST_RUSH = 2
    ST_DAMAGE = 3
    ST_DIE = 4

    def __init__(self, fill_width=False):
        self.frame = 0
        self.current_time = pg.time.get_ticks()
        self.updated_time = pg.time.get_ticks()
        self.cooldown = 111
        self.action = self.ST_IDLE
        self.alive = True
        self.animation = []
        # these loop creates surfaces for each action's frames
        for action in ["idle", "run", "rush", "damage", "die",]:
            # load image for the action
            image = self.__load_sprite(f"static/white-cat-{action}.png")
            # calculate how many frames it has
            frames = int(image.get_height() / self.HEIGHT)
            # actions actually store surfaces for each sprite
            action_frames = []
            for frame in range(frames):
                surface = pg.Surface((self.WIDTH, self.HEIGHT)).convert_alpha()
                surface.blit(image, (0, 0), (0, (frame * self.HEIGHT), self.WIDTH, self.HEIGHT))
                if fill_width:
                    surface = pg.transform.scale(surface, (400, 400))
                else:
                    surface = pg.transform.scale(surface, (self.WIDTH * self.SCALE, self.HEIGHT * self.SCALE))
                surface.set_colorkey(self.COLORKEY)
                action_frames.append(surface)
            self.animation.append(action_frames)
        pass

    def __load_sprite(self, image):
        return pg.image.load(image).convert_alpha()

    def set_action(self, action=ST_IDLE):
        self.action = action
        # if new action is death resetting the frame
        # makes the animation load
        if action == self.ST_DIE:
            self.frame = 0

    def display(self, root_surface):
        # frame updates only if the white car is alive
        if self.alive:
            # if its time to update the frame
            # cooldown is the time between rendering each frame
            self.current_time = pg.time.get_ticks()
            if self.current_time - self.updated_time >= self.cooldown:
                self.frame = (self.frame + 1) % len(self.animation[self.action])
                self.updated_time = self.current_time
            # check if it exceeds actions' frames
            if self.frame >= len(self.animation[self.action]):
                self.frame = 0
            # kill the car if its death animation's last frame
            if self.action == self.ST_DIE and self.frame == len(self.animation[self.action]) - 1:
                self.alive = False
            root_surface.blit(self.animation[self.action][self.frame], (0, 0))
        else:
            root_surface.blit(self.animation[self.ST_DIE][-1], (0, 0))


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
        self.white_car = WhiteCar(fill_width=True)
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
                self.white_car.set_action(action=WhiteCar.ST_IDLE)
            elif event.type == pg.MOUSEMOTION:
                if self.mouse_down:
                    self.white_car.set_action(action=WhiteCar.ST_DAMAGE)
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_q:
                    self.__set_running(False)
                elif event.key == pg.K_k:
                    self.white_car.set_action(WhiteCar.ST_DIE)
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

